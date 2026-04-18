"""
db.py — Supabase database and storage layer for AttentionXAI.

Design decisions:
  - Uses the synchronous supabase-py v2 client (httpx-based).
  - All public functions are declared `async def` so they integrate naturally
    with FastAPI and asyncio.  The actual Supabase I/O runs inside
    `asyncio.to_thread()` to avoid blocking the event loop.
  - The service-role key is used throughout; it bypasses Row-Level Security,
    which is intentional for a server-side worker.

Supabase resources used:
  Table  :  jobs
  Buckets:  attentionx-videos  (private — source uploads)
            attentionx-clips   (public  — processed clips)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY: str = os.environ["SUPABASE_SERVICE_KEY"]

VIDEOS_BUCKET: str = os.getenv("VIDEOS_BUCKET", "attentionx-videos")
CLIPS_BUCKET: str  = os.getenv("CLIPS_BUCKET",  "attentionx-clips")

JOBS_TABLE = "jobs"


# ─────────────────────────────────────────────────────────────────────────────
# Client factory
# supabase-py v2 client is thread-safe and can be reused across calls.
# ─────────────────────────────────────────────────────────────────────────────

_supabase_client: Client | None = None


def _get_client() -> Client:
    """Return a cached Supabase client (created once per process)."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized")
    return _supabase_client


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _run(fn, *args, **kwargs):
    """
    Wrap a synchronous Supabase call in asyncio.to_thread so it never
    blocks the FastAPI event loop.

    Usage:
        result = await _run(lambda: client.table("jobs").select("*").execute())
    """
    return await asyncio.to_thread(fn, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# DB lifecycle
# ─────────────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Verify Supabase connectivity on startup.
    Tables and buckets must already exist (see schema.sql).
    Raises an exception early if credentials are wrong.
    """
    def _ping():
        client = _get_client()
        client.table(JOBS_TABLE).select("id").limit(1).execute()

    try:
        await _run(_ping)
        logger.info("Supabase connection verified")
    except Exception as exc:
        logger.error(f"Supabase connection failed: {exc}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Job CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def create_job(
    job_id: str,
    filename: str,
    video_url: str,
    storage_path: str,
) -> dict[str, Any]:
    """
    Insert a new job row with status='queued'.

    Args:
        job_id:        Pre-generated UUID for this job.
        filename:      Original upload filename (for display only).
        video_url:     Supabase Storage public URL of the uploaded source video.
        storage_path:  Internal bucket path — used by the worker to download
                       the video for local processing (Whisper / MediaPipe).

    Returns:
        The inserted row as a dict.
    """
    payload: dict[str, Any] = {
        "id":           job_id,
        "status":       "queued",
        "filename":     filename,
        "video_url":    video_url,
        "storage_path": storage_path,
        "peaks":        None,
        "rms_array":    None,
        "duration":     None,
        "error_message": None,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }

    def _insert():
        return _get_client().table(JOBS_TABLE).insert(payload).execute()

    result = await _run(_insert)
    logger.info(f"Job created: {job_id}")
    return result.data[0]


async def get_job(job_id: str) -> dict[str, Any] | None:
    """
    Fetch a single job by ID.

    Returns:
        The job row dict, or None if not found.
    """
    def _select():
        return (
            _get_client()
            .table(JOBS_TABLE)
            .select("*")
            .eq("id", job_id)
            .execute()
        )

    result = await _run(_select)
    return result.data[0] if result.data else None


async def update_job(job_id: str, **kwargs: Any) -> dict[str, Any]:
    """
    Partial update — only the provided kwargs are written to Postgres.

    Supabase stores peaks/rms_array as JSONB; pass Python lists/dicts
    directly — supabase-py serialises them automatically.

    Examples::

        await update_job(job_id, status="transcribing")

        await update_job(
            job_id,
            status="done",
            peaks=[{...}, {...}],
            rms_array=[0.1, 0.3, ...],
            duration=3612.0,
        )
    """
    def _update():
        return (
            _get_client()
            .table(JOBS_TABLE)
            .update(kwargs)
            .eq("id", job_id)
            .execute()
        )

    result = await _run(_update)
    logger.debug(f"Job {job_id} updated: {list(kwargs.keys())}")
    return result.data[0] if result.data else {}


# ─────────────────────────────────────────────────────────────────────────────
# Storage — Video uploads (source files)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_video_to_storage(
    file_bytes: bytes,
    original_filename: str,
) -> tuple[str, str]:
    """
    Upload raw video bytes to the ``attentionx-videos`` bucket.

    The file is stored under a unique prefix to avoid collisions.
    The bucket is private, so the returned "public URL" is actually a
    signed/internal URL — configure the bucket as public in the Supabase
    dashboard if you want direct browser access.

    Args:
        file_bytes:        Raw bytes of the uploaded video.
        original_filename: Original filename (e.g. "lecture.mp4").

    Returns:
        (storage_path, public_url)
          storage_path — internal path inside the bucket (used by worker
                         to download the file via ``download_video_from_storage``)
          public_url   — Supabase public URL (stored in jobs.video_url)
    """
    ext = Path(original_filename).suffix or ".mp4"
    prefix = str(uuid4())
    storage_path = f"{prefix}/original{ext}"

    def _upload():
        client = _get_client()
        client.storage.from_(VIDEOS_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": "video/mp4",
                "upsert": "true",
            },
        )
        return client.storage.from_(VIDEOS_BUCKET).get_public_url(storage_path)

    public_url: str = await _run(_upload)
    logger.info(f"Video uploaded → {storage_path} ({len(file_bytes):,} bytes)")
    return storage_path, public_url


async def download_video_from_storage(
    storage_path: str,
    local_dest: str,
) -> None:
    """
    Download a video from Supabase Storage to a local path.

    Required because Whisper, LibROSA, MediaPipe, and MoviePy all need
    a local filesystem path — they cannot stream from a URL.

    Args:
        storage_path: Internal bucket path (as returned by upload_video_to_storage).
        local_dest:   Absolute local path to write the file to.
    """
    def _download():
        return _get_client().storage.from_(VIDEOS_BUCKET).download(storage_path)

    file_bytes: bytes = await _run(_download)

    local_path = Path(local_dest)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    with open(local_path, "wb") as f:
        f.write(file_bytes)

    logger.info(f"Video downloaded from storage → {local_dest} ({len(file_bytes):,} bytes)")


# ─────────────────────────────────────────────────────────────────────────────
# Storage — Clip uploads (processed outputs)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_clip_to_storage(
    local_clip_path: str,
    clip_id: str,
) -> str:
    """
    Upload a processed 9:16 clip MP4 to the ``attentionx-clips`` bucket.

    The clips bucket should be configured as **public** in Supabase so that
    the frontend can stream/download clips without authentication.

    Args:
        local_clip_path: Absolute local path of the rendered MP4.
        clip_id:         UUID used as the storage filename (``<clip_id>.mp4``).

    Returns:
        Public URL of the uploaded clip (stored inside jobs.peaks[].clip_url).
    """
    storage_path = f"{clip_id}.mp4"

    with open(local_clip_path, "rb") as f:
        file_bytes = f.read()

    def _upload():
        client = _get_client()
        client.storage.from_(CLIPS_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": "video/mp4",
                "upsert": "true",
            },
        )
        return client.storage.from_(CLIPS_BUCKET).get_public_url(storage_path)

    public_url: str = await _run(_upload)
    logger.info(f"Clip uploaded → {storage_path} ({len(file_bytes):,} bytes)")
    return public_url


async def get_clip_url_by_id(clip_id: str) -> str | None:
    """
    Look up the Supabase public URL of a clip by its clip_id.

    Searches the JSONB peaks array across all jobs.
    Suitable for MVP scale; add a dedicated ``clips`` table for production.

    Returns:
        The public URL string, or None if not found.
    """
    def _search():
        # Use Postgres JSONB containment: peaks @> [{"clip_id": "..."}]
        return (
            _get_client()
            .table(JOBS_TABLE)
            .select("peaks")
            .filter("peaks", "cs", f'[{{"clip_id":"{clip_id}"}}]')
            .execute()
        )

    result = await _run(_search)

    for row in result.data:
        peaks = row.get("peaks") or []
        for peak in peaks:
            if peak.get("clip_id") == clip_id:
                return peak.get("clip_url")

    return None
