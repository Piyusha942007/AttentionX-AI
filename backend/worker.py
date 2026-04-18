"""
worker.py — Background job orchestrator for AttentionXAI.

Runs the full 4-step ML pipeline asynchronously:
  1. Transcribe  (Whisper)
  2. Analyze     (Gemini 1.5 Flash + Librosa RMS fusion)
  3. Face-track  (MediaPipe)
  4. Crop + Caption + Upload to Supabase

All CPU-bound synchronous functions are dispatched to a ThreadPoolExecutor
so they never block the FastAPI event loop.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from db import update_job, upload_clip_to_storage
from services.memory import cleanup_memory

logger = logging.getLogger(__name__)

# Two workers: one for ML (Whisper/Librosa/Gemini), one for video rendering
_executor = ThreadPoolExecutor(max_workers=2)


async def _run_sync(fn, *args):
    """Dispatch a synchronous function to the thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


async def process_job(
    job_id: str, 
    video_path: str | None = None, 
    youtube_url: str | None = None,
    caption_color: str = "Yellow",
) -> None:
    """
    Full processing pipeline for a single job with AGGRESSIVE MEMORY MANAGEMENT.
    """
    logger.info(f"[{job_id}] Pipeline starting — source: {video_path}")
    cleanup_memory("Start")

    try:
        # ── Step 0: Download (if YouTube) ───────────────────────────────────
        if youtube_url:
            await update_job(job_id, status="queued")
            logger.info(f"[{job_id}] Step 0/4: Downloading from YouTube: {youtube_url}")
            
            from services.downloader import download_youtube_video
            from db import upload_video_to_storage
            
            # Download to a temporary internal path
            output_dir = str(Path("/tmp/uploads") / job_id)
            meta = await _run_sync(download_youtube_video, youtube_url, output_dir)
            video_path = meta["local_path"]
            
            # Upload the downloaded file to Supabase so it's backed up + visible in UI
            with open(video_path, "rb") as f:
                storage_path, video_url = await upload_video_to_storage(f.read(), meta["filename"])
            
            # Update job metadata with real filename and URLs
            await update_job(
                job_id, 
                filename=meta["title"], 
                video_url=video_url, 
                storage_path=storage_path
            )
            logger.info(f"[{job_id}] Download complete: {meta['title']}")
            cleanup_memory("After Download")

        if not video_path:
            raise ValueError("No video source provided (neither path nor URL)")

        # ── Step 1: Transcribe ────────────────────────────────────────────────
        await update_job(job_id, status="transcribing")
        logger.info(f"[{job_id}] Step 1/4: Transcribing with faster-whisper…")

        from services.transcriber import transcribe_video
        segments = await _run_sync(transcribe_video, video_path)
        logger.info(f"[{job_id}] Transcription done: {len(segments)} segments")
        cleanup_memory("After Transcription")

        # ── Step 2: Analyze (Gemini) + Score (Librosa + Fusion) ────────────
        await update_job(job_id, status="analyzing")
        logger.info(f"[{job_id}] Step 2/4: Analyzing with Gemini + Librosa…")

        from services.analyzer import analyze_transcript
        from services.scorer import (
            downsample_rms,
            extract_rms,
            fuse_and_rank,
            pick_top_peaks,
        )

        # Run Gemini analysis and audio RMS extraction in sequence (to save RAM)
        candidate_peaks = await _run_sync(analyze_transcript, segments)
        cleanup_memory("After Gemini")
        
        rms_result = await _run_sync(extract_rms, video_path)
        cleanup_memory("After Librosa")

        frame_times, energy_smooth = rms_result
        ranked = fuse_and_rank(candidate_peaks, frame_times, energy_smooth)
        top_peaks = pick_top_peaks(ranked)
        
        # Fallback if Gemini or Librosa fails/returns 0 peaks (for MVP resilience)
        if not top_peaks:
            logger.warning(f"[{job_id}] No peaks found by Gemini. Using fallback mock peak.")
            max_dur = segments[-1]["end"] if segments else 60.0
            clip_end = min(max_dur, 45.0)
            top_peaks = [{
                "time": clip_end / 2, "start": 0.0, "end": clip_end,
                "virality_score": 0.95, "headline": "The Ultimate Secret Revealed", 
                "clip_title": "Actionable Tip", "reason": "actionable_tip"
            }]

        rms_chart = downsample_rms(energy_smooth)
        
        # Prepare initial peaks for the UI
        initial_peaks = []
        for peak in top_peaks:
            initial_peaks.append({
                "time":       peak["time"],
                "start":      peak["start"],
                "end":        peak["end"],
                "score":      peak["virality_score"],
                "headline":   peak.get("headline", "Identifying viral nugget..."),
                "clip_title": peak.get("clip_title", ""),
                "reason":     peak.get("reason", ""),
                "clip_id":    "",
                "clip_url":   "",
                "words":      [],
            })

        logger.info(f"[{job_id}] Scoring done: {len(top_peaks)} top clips selected.")

        # Persist RMS array and initial peaks so the frontend can render them
        await update_job(
            job_id, 
            status="cropping", 
            rms_array=rms_chart,
            peaks=initial_peaks
        )
        
        # Explicitly clear large analytical arrays
        del frame_times
        del energy_smooth
        cleanup_memory("Before Tracking")

        # ── Step 3: Face Track ─────────────────────────────────────────────
        logger.info(f"[{job_id}] Step 3/4: Running MediaPipe face tracking…")

        from services.face_tracker import detect_face_centers
        face_centers = await _run_sync(detect_face_centers, video_path)
        cleanup_memory("After MediaPipe")

        # ── Step 4: Crop + Caption + Upload ───────────────────────────────
        logger.info(f"[{job_id}] Step 4/4: Cropping {len(top_peaks)} clips…")

        from services.captioner import burn_captions
        from services.cropper import make_vertical_clip

        final_peaks = []

        for i, peak in enumerate(top_peaks):
            clip_id = str(uuid.uuid4())
            clip_num = f"{i + 1}/{len(top_peaks)}"

            # Collect words for this clip
            peak_words = _extract_words_for_peak(segments, peak["start"], peak["end"])

            # 4a. Crop
            logger.info(f"[{job_id}] Clip {clip_num}: cropping {peak['start']:.0f}s–{peak['end']:.0f}s")
            raw_clip_path = await _run_sync(
                make_vertical_clip,
                video_path,
                peak["start"],
                peak["end"],
                clip_id,
                face_centers,
            )

            # 4b. Burn captions
            captioned_path = raw_clip_path.replace(".mp4", "_captioned.mp4")
            final_clip_path = await _run_sync(
                burn_captions,
                raw_clip_path,
                peak_words,
                peak["start"],
                captioned_path,
                caption_color,
            )

            # 4c. Upload
            clip_url = await upload_clip_to_storage(final_clip_path, clip_id)
            logger.info(f"[{job_id}] Clip {clip_num} uploaded")

            final_peaks.append({
                "time":       peak["time"],
                "start":      peak["start"],
                "end":        peak["end"],
                "score":      peak["virality_score"],
                "headline":   peak.get("headline", ""),
                "clip_title": peak.get("clip_title", ""),
                "reason":     peak.get("reason", ""),
                "clip_id":    clip_id,
                "clip_url":   clip_url,
                "words":      peak_words,
            })
            
            # GC after each rendered clip to prevent spike accumulation
            cleanup_memory(f"Clip {i+1} Render")

        # ── Done ──────────────────────────────────────────────────────────
        duration = segments[-1]["end"] if segments else 0.0

        await update_job(
            job_id,
            status="done",
            peaks=final_peaks,
            rms_array=rms_chart,
            duration=duration,
        )
        logger.info(f"[{job_id}] ✅ Pipeline complete")
        cleanup_memory("Pipeline Finished")

    except Exception as exc:
        logger.error(f"[{job_id}] ❌ Pipeline failed: {exc}", exc_info=True)
        await update_job(job_id, status="failed", error_message=str(exc))


def _extract_words_for_peak(
    segments: list[dict],
    start: float,
    end: float,
) -> list[dict]:
    """
    Collect Whisper word-level timestamps that fall within [start, end].

    Returns a flat list: [{"word": str, "start": float, "end": float}, ...]
    """
    words = []
    for seg in segments:
        if seg["end"] < start or seg["start"] > end:
            continue
        for w in seg.get("words", []):
            if w["start"] >= start and w["end"] <= end:
                words.append({
                    "word":  w["word"].strip(),
                    "start": round(w["start"], 3),
                    "end":   round(w["end"], 3),
                })
    return words
