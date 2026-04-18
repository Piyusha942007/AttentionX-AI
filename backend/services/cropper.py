"""
cropper.py — MoviePy vertical crop engine for 9:16 TikTok/Reels output.

Takes a 16:9 source (1920×1080) and produces a 608×1080 MP4 where the
crop window follows the speaker's face using per-frame offsets from
face_tracker.detect_face_centers().

Output: H.264 / AAC, 30 fps, libx264 'fast' preset (PRD spec).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

# Configure MoviePy to use local ffmpeg binary (v2.x compatible)
BACKEND_DIR = Path(__file__).parent.parent
FFMPEG_EXE = str(BACKEND_DIR / "ffmpeg.exe")
os.environ["MOVIEPY_FFMPEG_BINARY"] = FFMPEG_EXE

from moviepy import VideoFileClip

from .face_tracker import CROP_W, get_crop_x

logger = logging.getLogger(__name__)

OUTPUT_DIR    = Path(os.getenv("OUTPUT_DIR", "./output_clips"))
TARGET_HEIGHT = 1080
TARGET_WIDTH  = CROP_W  # 608


def make_vertical_clip(
    source_path:        str,
    start:              float,
    end:                float,
    clip_id:            str,
    face_centers_full:  list[int],
) -> str:
    """
    Crop a segment of the source video to 9:16 vertical format using
    per-frame face-tracking offsets.

    Args:
        source_path:       Local path to the full-length source video.
        start:             Clip start time in seconds.
        end:               Clip end time in seconds.
        clip_id:           UUID — used as the output filename.
        face_centers_full: Per-frame smoothed face center X array for the
                           entire video (from face_tracker.detect_face_centers).

    Returns:
        Local path to the exported 608×1080 MP4 file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(OUTPUT_DIR / f"{clip_id}.mp4")

    logger.info(f"Cropping clip {clip_id}: {start:.1f}s – {end:.1f}s → {output_path}")

    source_clip = VideoFileClip(source_path)
    clip        = source_clip.subclipped(start, end)
    clip_fps    = clip.fps or 30.0
    frame_w     = clip.w
    frame_h     = clip.h

    # Starting frame index in the full-video face_centers array
    start_frame = int(start * clip_fps)
    n_centers   = len(face_centers_full)

    # ── Per-frame crop function (called by MoviePy fl()) ──────────────────

    def crop_frame(get_frame, t: float):
        frame = get_frame(t)
        abs_frame_idx = start_frame + int(t * clip_fps)

        # Fetch smoothed center X; fall back to frame center if out of range
        if abs_frame_idx < n_centers:
            cx = face_centers_full[abs_frame_idx]
        else:
            cx = frame_w // 2

        x = get_crop_x(cx, frame_w)

        # Horizontal crop to TARGET_WIDTH (608px)
        cropped = frame[:, x: x + TARGET_WIDTH]

        # Vertical crop to TARGET_HEIGHT if source is taller (rare for 1080p)
        h = cropped.shape[0]
        if h > TARGET_HEIGHT:
            y0 = (h - TARGET_HEIGHT) // 2
            cropped = cropped[y0: y0 + TARGET_HEIGHT]

        return cropped

    # ── Apply and export ──────────────────────────────────────────────────

    vertical = clip.transform(crop_frame, apply_to="mask")

    vertical.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        preset="fast",
        audio_codec="aac",
        temp_audiofile=str(OUTPUT_DIR / f"{clip_id}_tmp_audio.m4a"),
        remove_temp=True,
        logger=None,   # suppress MoviePy's built-in progress bar
    )

    clip.close()
    source_clip.close()
    vertical.close()

    logger.info(f"Clip exported: {output_path}")
    return output_path
