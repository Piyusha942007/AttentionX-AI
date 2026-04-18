"""
transcriber.py — Whisper-based audio transcription with MD5 disk caching.

Returns word-level timestamped segments compatible with the Integration Contract.
Caching avoids re-running Whisper on the same video during development.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

import whisper  # openai-whisper

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache/transcripts"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Lazy-loaded model — loaded once per process on first call
_model: whisper.Whisper | None = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        # Using 'tiny' model to fit within Render Free/Starter RAM limits (512MB)
        logger.info("Loading Whisper 'tiny' model (optimized for low RAM)…")
        _model = whisper.load_model("tiny")
        logger.info("Whisper model loaded")
    return _model


def _video_md5(video_path: str) -> str:
    """Compute MD5 of the first 8 MB + last 8 MB for a fast fingerprint."""
    h = hashlib.md5()
    chunk = 8 * 1024 * 1024  # 8 MB
    with open(video_path, "rb") as f:
        h.update(f.read(chunk))
        try:
            f.seek(-chunk, 2)
            h.update(f.read(chunk))
        except OSError:
            pass  # file smaller than 8 MB
    return h.hexdigest()


def transcribe_video(video_path: str) -> list[dict]:
    """
    Transcribe a video/audio file using Whisper with word-level timestamps.

    Results are cached to disk by a partial MD5 of the video so repeated
    runs during development never re-invoke Whisper.

    Args:
        video_path: Local path to an MP4/MOV/MKV/WAV file.

    Returns:
        List of segment dicts::

            [
              {
                "start": 0.0,
                "end":   3.2,
                "text":  "The biggest mistake founders make…",
                "words": [
                  {"word": "The",      "start": 0.0,  "end": 0.3},
                  {"word": "biggest",  "start": 0.3,  "end": 0.7},
                  ...
                ]
              },
              ...
            ]
    """
    video_hash = _video_md5(video_path)
    cache_file = CACHE_DIR / f"{video_hash}.json"

    if cache_file.exists():
        logger.info(f"Transcript cache hit → {cache_file.name}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Transcribing: {video_path}")
    model = _get_model()

    result = model.transcribe(
        video_path,
        word_timestamps=True,
        verbose=False,
    )

    segments: list[dict] = []
    for seg in result["segments"]:
        words = [
            {
                "word":  w["word"].strip(),
                "start": round(float(w["start"]), 3),
                "end":   round(float(w["end"]),   3),
            }
            for w in seg.get("words", [])
        ]
        segments.append({
            "start": round(float(seg["start"]), 3),
            "end":   round(float(seg["end"]),   3),
            "text":  seg["text"].strip(),
            "words": words,
        })

    # Write cache
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False)

    logger.info(f"Transcription complete: {len(segments)} segments → cached as {cache_file.name}")
    return segments
