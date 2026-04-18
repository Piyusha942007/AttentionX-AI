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
    youtube_url: str | None = None
) -> None:
    """
    Full processing pipeline for a single job.

    Status transitions written to Supabase at each step:
        queued → transcribing → analyzing → cropping → done
        (or → failed on any exception)

    Args:
        job_id:     Supabase job UUID.
        video_path: Local filesystem path to the uploaded video file.
    """
    logger.info(f"[{job_id}] Pipeline starting — source: {video_path}")

    try:
        # ── Step 0: Download (if YouTube) ───────────────────────────────────
        if youtube_url:
            await update_job(job_id, status="downloading")
            logger.info(f"[{job_id}] Step 0/4: Downloading from YouTube: {youtube_url}")
            
            from services.downloader import download_youtube_video
            from db import upload_video_to_storage
            
            # Download to a temporary internal path
            output_dir = str(Path("backend/uploads") / job_id)
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

        if not video_path:
            raise ValueError("No video source provided (neither path nor URL)")

        # ── Step 1: Transcribe ────────────────────────────────────────────────
        await update_job(job_id, status="transcribing")
        logger.info(f"[{job_id}] Step 1/4: Transcribing with Whisper…")

        from services.transcriber import transcribe_video
        segments = await _run_sync(transcribe_video, video_path)
        logger.info(f"[{job_id}] Transcription done: {len(segments)} segments")

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

        # Run Gemini analysis and audio RMS extraction in parallel (both sync)
        candidate_peaks, rms_result = await asyncio.gather(
            _run_sync(analyze_transcript, segments),
            _run_sync(extract_rms, video_path),
        )

        frame_times, energy_smooth = rms_result
        ranked = fuse_and_rank(candidate_peaks, frame_times, energy_smooth)
        top_peaks = pick_top_peaks(ranked)
        rms_chart = downsample_rms(energy_smooth)
        
        # NEW: Prepare partial peaks for progressive discovery
        # These appear in the UI as "Rendering..." immediately after analysis
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
                "clip_id":    None,
                "clip_url":   None,
                "words":      [],
            })

        logger.info(
            f"[{job_id}] Scoring done: {len(candidate_peaks)} candidates → "
            f"{len(top_peaks)} top clips selected. Updating UI for progressive discovery."
        )

        # Persist RMS array and initial peaks so the frontend can render them
        # while cropping is still running
        await update_job(
            job_id, 
            status="cropping", 
            rms_array=rms_chart,
            peaks=initial_peaks
        )

        # ── Step 3: Face Track ─────────────────────────────────────────────
        logger.info(f"[{job_id}] Step 3/4: Running MediaPipe face tracking…")

        from services.face_tracker import detect_face_centers
        face_centers = await _run_sync(detect_face_centers, video_path)

        # ── Step 4: Crop + Caption + Upload ───────────────────────────────
        logger.info(f"[{job_id}] Step 4/4: Cropping {len(top_peaks)} clips…")

        from services.captioner import burn_captions
        from services.cropper import make_vertical_clip

        final_peaks = []

        for i, peak in enumerate(top_peaks):
            clip_id = str(uuid.uuid4())
            clip_num = f"{i + 1}/{len(top_peaks)}"

            # Collect Whisper word timestamps for this clip's time range
            peak_words = _extract_words_for_peak(segments, peak["start"], peak["end"])

            # 4a. Crop to 9:16 vertical
            logger.info(f"[{job_id}] Clip {clip_num}: cropping {peak['start']:.0f}s–{peak['end']:.0f}s")
            raw_clip_path = await _run_sync(
                make_vertical_clip,
                video_path,
                peak["start"],
                peak["end"],
                clip_id,
                face_centers,
            )

            # 4b. Burn karaoke captions
            captioned_path = raw_clip_path.replace(".mp4", "_captioned.mp4")
            final_clip_path = await _run_sync(
                burn_captions,
                raw_clip_path,
                peak_words,
                peak["start"],
                captioned_path,
            )

            # 4c. Upload finished clip to Supabase Storage
            clip_url = await upload_clip_to_storage(final_clip_path, clip_id)
            logger.info(f"[{job_id}] Clip {clip_num} uploaded → {clip_url}")

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

        # ── Done ──────────────────────────────────────────────────────────
        # Calculate video duration from the last segment's end time
        duration = segments[-1]["end"] if segments else 0.0

        await update_job(
            job_id,
            status="done",
            peaks=final_peaks,
            rms_array=rms_chart,
            duration=duration,
        )
        logger.info(f"[{job_id}] ✅ Pipeline complete: {len(final_peaks)} clips ready")

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
