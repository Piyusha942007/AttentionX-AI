import hashlib
import json
import logging
import os
import gc
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache/transcripts"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Model Configuration ─────────────────────────────────────────────────────

# For Render's 512MB Free tier, 'tiny' is the only safe bet.
# compute_type="int8" reduces RAM usage significantly.
_WHISPER_MODEL_NAME = "tiny"
_COMPUTE_TYPE = "int8"

def _video_md5(video_path: str) -> str:
    """Compute MD5 of the first 8 MB + last 8 MB for a fast fingerprint."""
    h = hashlib.md5()
    chunk = 8 * 1024 * 1024  # 8 MB
    with open(video_path, "rb") as f:
        data = f.read(chunk)
        h.update(data)
        try:
            f.seek(-chunk, 2)
            h.update(f.read(chunk))
        except OSError:
            pass  # file smaller than 8 MB
    return h.hexdigest()

def transcribe_video(video_path: str) -> list[dict]:
    """
    Transcribe a video/audio file using faster-whisper with word-level timestamps.
    Results are cached to disk.
    """
    video_hash = _video_md5(video_path)
    cache_file = CACHE_DIR / f"{video_hash}.json"

    if cache_file.exists():
        logger.info(f"Transcript cache hit → {cache_file.name}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Transcribing: {video_path}")
    
    # Load model just-in-time for the call
    model = WhisperModel(
        _WHISPER_MODEL_NAME, 
        device="cpu", 
        compute_type=_COMPUTE_TYPE,
        download_root="./models/whisper"
    )

    try:
        # Run transcription
        segments_gen, _ = model.transcribe(video_path, word_timestamps=True, beam_size=1)
        
        segments: list[dict] = []
        for seg in segments_gen:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word":  w.word.strip(),
                        "start": round(float(w.start), 3),
                        "end":   round(float(w.end),   3),
                    })
            
            segments.append({
                "start": round(float(seg.start), 3),
                "end":   round(float(seg.end),   3),
                "text":  seg.text.strip(),
                "words": words,
            })

        # Write cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False)

        logger.info(f"Transcription complete: {len(segments)} segments → cached as {cache_file.name}")
        return segments
    finally:
        # AGGRESSIVE CLEANUP
        logger.info("Unloading Whisper model and performing GC...")
        del model
        gc.collect()
