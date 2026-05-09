"""
cropper.py — FFmpeg vertical crop engine for 9:16 TikTok/Reels output.

Takes a 16:9 source (1920×1080) and produces a 608×1080 MP4 using
a static crop window based on the average face center for the segment.
This replaces MoviePy to achieve Zero-RAM usage on Render.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
import cv2

# Configure ffmpeg cross-platform (local .exe vs global Linux binary)
if os.name == "nt":
    BACKEND_DIR = Path(__file__).parent.parent
    FFMPEG_EXE = str(BACKEND_DIR / "ffmpeg.exe")
else:
    FFMPEG_EXE = "ffmpeg"

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
    true dynamic per-frame cropping via OpenCV and FFmpeg stdin piping.

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

    # Use cv2 to get accurate FPS and dimensions
    cap = cv2.VideoCapture(source_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if not fps or fps <= 0:
        fps = 30.0
    if not frame_h or frame_h <= 0:
        frame_h = 1080
    if not frame_w or frame_w <= 0:
        frame_w = 1920

    start_frame = int(start * fps)
    end_frame = int(end * fps)
    total_clip_frames = end_frame - start_frame
    
    # Target dimension
    crop_w = int(frame_h * 9 / 16)
    duration = end - start

    # ── FFmpeg Raw Input Pipeline ──────────────────────────────────────────
    # We pipe raw BGR bytes from cv2 into ffmpeg for extremely fast,
    # zero-RAM encoding. We also map audio from the original file.
    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{crop_w}x{frame_h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",               # Input 0: Raw video from stdin
        "-ss", str(start),
        "-i", source_path,       # Input 1: Original video for audio
        "-t", str(duration),
        "-map", "0:v:0",         # Use stdin video
        "-map", "1:a:0?",        # Use original audio (if exists)
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-threads", "2",
        "-shortest",
        output_path
    ]

    try:
        # Open FFmpeg subprocess (using DEVNULL for stderr to prevent OS pipe buffer deadlock)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # Seek to start frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        n_centers = len(face_centers_full)
        
        for i in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break
                
            # Fallback to frame center if array is short
            cx = face_centers_full[i] if i < n_centers else (frame_w // 2)
            x = get_crop_x(int(cx), frame_w, frame_h)
            
            # Dynamic crop for this exact frame
            cropped = frame[:, x : x + crop_w]
            
            # Write raw bytes to FFmpeg
            proc.stdin.write(cropped.tobytes())
            
        # Close stdin to signal EOF to FFmpeg
        proc.stdin.close()
        
        # Wait for FFmpeg to finish encoding
        proc.wait()
        
        if proc.returncode != 0:
            logger.error(f"FFmpeg dynamic crop failed with return code {proc.returncode}")
            raise Exception("FFmpeg failed to encode dynamic crop.")
            
    except Exception as e:
        logger.error(f"Exception during dynamic crop: {e}")
        raise
    finally:
        cap.release()

    logger.info(f"Clip exported: {output_path}")
    return output_path
