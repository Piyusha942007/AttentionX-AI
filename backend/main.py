"""
main.py — FastAPI application for AttentionXAI.

Endpoints:
  POST /api/jobs                   — Upload video, create job, start pipeline
  GET  /api/jobs/{job_id}          — Poll job status + results
  GET  /api/clips/{clip_id}/download — Redirect to Supabase clip URL
  GET  /api/jobs/mock/demo         — Pre-built completed job for UI smoke-testing
"""
from __future__ import annotations

import logging
import math
import os
import random
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from db import (
    create_job,
    download_video_from_storage,
    get_clip_url_by_id,
    get_job,
    init_db,
    upload_video_to_storage,
)
from models import JobCreateResponse, JobResponse, JobStatus, Peak
from pydantic import BaseModel, HttpUrl

class YouTubeJobRequest(BaseModel):
    url: str

from worker import process_job

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# App lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify Supabase connection on startup."""
    await init_db()
    yield


app = FastAPI(
    title="AttentionXAI API",
    description="Viral clip extraction pipeline for long-form video",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file (MP4/MOV/MKV)"),
):
    """
    Accept a video upload, store it in Supabase, create a job row,
    and kick off the background processing pipeline.
    """
    job_id = str(uuid.uuid4())

    # 1. Read bytes from multipart upload
    file_bytes = await file.read()
    logger.info(f"Received upload: {file.filename} ({len(file_bytes):,} bytes)")

    # 2. Upload source video to Supabase Storage (private bucket)
    storage_path, video_url = await upload_video_to_storage(file_bytes, file.filename)

    # 3. Also save locally so the worker can access it immediately
    #    (avoids an extra download round-trip for the first run)
    local_path = UPLOAD_DIR / f"{job_id}{Path(file.filename).suffix}"
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    # 4. Create job row in Supabase Postgres
    await create_job(
        job_id=job_id,
        filename=file.filename,
        video_url=video_url,
        storage_path=storage_path,
    )

    # 5. Fire background pipeline (non-blocking)
    background_tasks.add_task(process_job, job_id, str(local_path))

    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@app.post("/api/jobs/youtube", response_model=JobCreateResponse, status_code=202)
async def create_youtube_job_endpoint(
    request: YouTubeJobRequest,
    background_tasks: BackgroundTasks,
):
    """
    Accept a YouTube URL, create a job row, and start the download+analysis pipeline.
    """
    job_id = str(uuid.uuid4())
    url_str = str(request.url)

    # 1. Create job row (no video_url yet, will be filled after download & storage upload)
    await create_job(
        job_id=job_id,
        filename=f"YouTube: {url_str}",
        video_url="",
        storage_path="",
    )

    # 2. Fire background pipeline with the URL
    background_tasks.add_task(process_job, job_id, video_path=None, youtube_url=url_str)

    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@app.get("/api/jobs/mock/demo", response_model=JobResponse)
async def get_mock_job():
    """
    Return a pre-built completed job for UI smoke-testing.
    Lets the frontend be fully validated without running the ML pipeline.
    """
    # Synthetic waveform — sine + noise
    rms = [
        round(0.25 + 0.55 * abs(math.sin(i / 18)) + random.uniform(-0.04, 0.04), 3)
        for i in range(500)
    ]

    mock_peaks = [
        Peak(
            time=42.3,  start=12.3,  end=72.3,  score=0.94,
            headline="The $0 marketing strategy nobody talks about",
            clip_title="Zero Budget Growth", reason="actionable_tip",
            clip_id="mock-clip-1", clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        ),
        Peak(
            time=310.0, start=280.0, end=340.0, score=0.86,
            headline="I failed 7 times before this worked",
            clip_title="Failure as Fuel",   reason="personal_story",
            clip_id="mock-clip-2", clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        ),
        Peak(
            time=720.5, start=690.5, end=750.5, score=0.68,
            headline="Most founders get this completely backwards",
            clip_title="Founder Blind Spot", reason="counterintuitive_claim",
            clip_id="mock-clip-3", clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        ),
        Peak(
            time=1240.0, start=1210.0, end=1270.0, score=0.85,
            headline="One question that changed everything for me",
            clip_title="The Game-Changer", reason="quotable_one_liner",
            clip_id="mock-clip-4", clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        ),
        Peak(
            time=2100.3, start=2070.3, end=2130.3, score=0.79,
            headline="Nobody tells you this at 30 but you need to hear it",
            clip_title="30-Year Truth Bomb", reason="emotional_peak",
            clip_id="mock-clip-5", clip_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        ),
    ]

    return JobResponse(
        job_id="mock-demo-obsidian",
        status=JobStatus.done,
        filename="viral_marketing_workshop.mp4",
        duration=3612.0,
        rms_array=rms,
        peaks=mock_peaks,
        created_at="2026-01-15T09:00:00Z",
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_endpoint(job_id: str):
    """Poll job status and results."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Deserialize JSONB peaks → Peak models
    raw_peaks = job.get("peaks") or []
    peaks = [Peak(**p) for p in raw_peaks]

    return JobResponse(
        job_id=job["id"],
        status=JobStatus(job["status"]),
        filename=job.get("filename", ""),
        peaks=peaks,
        rms_array=job.get("rms_array") or [],
        duration=job.get("duration") or 0.0,
        error_message=job.get("error_message"),
        created_at=str(job.get("created_at", "")),
    )


@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """
    Redirect the browser to the Supabase Storage public URL for this clip.
    The clip_url is stored inside jobs.peaks[].clip_url (JSONB).
    """
    clip_url = await get_clip_url_by_id(clip_id)
    if not clip_url:
        raise HTTPException(status_code=404, detail=f"Clip '{clip_id}' not found")
    return RedirectResponse(url=clip_url, status_code=302)


# ─────────────────────────────────────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
