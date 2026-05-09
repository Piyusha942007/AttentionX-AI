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
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Form
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
    caption_color: str = "Yellow"

class ExportClipRequest(BaseModel):
    caption_color: str = "Yellow"

from worker import process_job
from services.captioner import burn_captions
from services.memory import cleanup_memory

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

# Allowed origins for the production MVP/Vercel deployment
origins = [
    "http://localhost:5173",
    "https://attention-x-ai.vercel.app",
    "https://attentionxai.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Keeping "*" for MVP but explicitly mentioning origins for preflight reliability
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file (MP4/MOV/MKV)"),
    caption_color: str = Form("Yellow"),
):
    """
    Accept a video upload, store it in Supabase, create a job row,
    and kick off the background processing pipeline.
    """
    job_id = str(uuid.uuid4())

    # 1. Stream file directly to local disk (Zero-RAM mode)
    local_path = UPLOAD_DIR / f"{job_id}{Path(file.filename).suffix}"
    
    with open(local_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
            
    logger.info(f"Received upload and saved to: {local_path}")

    # 2. Upload source video to Supabase Storage using the local path
    storage_path, video_url = await upload_video_to_storage(str(local_path), file.filename)

    # 4. Create job row in Supabase Postgres
    await create_job(
        job_id=job_id,
        filename=file.filename,
        video_url=video_url,
        storage_path=storage_path,
    )

    # 5. Fire background pipeline (non-blocking)
    background_tasks.add_task(process_job, job_id, str(local_path), youtube_url=None, caption_color=caption_color)

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
    background_tasks.add_task(process_job, job_id, video_path=None, youtube_url=url_str, caption_color=request.caption_color)

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


@app.post("/api/clips/{job_id}/{clip_id}/export")
async def export_clip_endpoint(
    job_id: str,
    clip_id: str,
    request: ExportClipRequest,
):
    """
    Render a final version of a clip with burned-in captions in a specific color.
    
    1. Fetch job to get words for this clip
    2. Download raw vertical clip from Supabase
    3. Burn captions
    4. Upload final version
    5. Return public URL
    """
    # 1. Fetch job
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Find the specific peak/clip
    peaks = job.get("peaks") or []
    target_peak = next((p for p in peaks if p.get("clip_id") == clip_id), None)
    if not target_peak:
        raise HTTPException(status_code=404, detail="Clip not found in job")
    
    # 2. Download raw clip
    # (Using a temp directory for processing)
    temp_dir = UPLOAD_DIR / "exports" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    raw_clip_name = f"{clip_id}_raw.mp4"
    local_raw_path = temp_dir / raw_clip_name
    
    # We need a way to download from CLIPS_BUCKET
    from db import _get_client, _run, CLIPS_BUCKET, upload_clip_to_storage
    
    def _download_raw():
        return _get_client().storage.from_(CLIPS_BUCKET).download(f"{clip_id}.mp4")
    
    try:
        file_bytes = await _run(_download_raw)
        with open(local_raw_path, "wb") as f:
            f.write(file_bytes)
            
        # 3. Burn captions
        output_name = f"{clip_id}_final_{request.caption_color}.mp4"
        local_output_path = temp_dir / output_name
        
        final_path = await asyncio.to_thread(
            burn_captions,
            str(local_raw_path),
            target_peak["words"],
            target_peak["start"],
            str(local_output_path),
            request.caption_color
        )
        
        # 4. Upload final version
        # Use a new ID for the final version to avoid overwriting the raw preview
        final_id = f"{clip_id}_{request.caption_color.lower()}"
        final_url = await upload_clip_to_storage(final_path, final_id)
        
        # Cleanup
        cleanup_memory("Export Finish")
        try:
            os.remove(local_raw_path)
            os.remove(local_output_path)
        except:
            pass
            
        return {"download_url": final_url}
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
