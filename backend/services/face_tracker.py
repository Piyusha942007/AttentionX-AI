"""
face_tracker.py — MediaPipe face detection with smoothed per-frame crop offsets.

Strategy:
  1. Run MediaPipe FaceDetection every FRAME_SKIP frames (default 3)
     for a ~3× speed-up over full per-frame detection.
  2. Linearly interpolate the center X between detected keyframes.
  3. Apply a 30-frame rolling average (scipy uniform_filter1d) to
     eliminate jitter that would cause distracting crop-window wobble.
  4. Convert center X to a left-edge X offset (clamped inside frame bounds).

Edge case: if no face is detected for a segment, default to frame center.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np
from scipy.ndimage import uniform_filter1d

# Attempt to load MediaPipe solutions; handle environments where it's missing (e.g. Python 3.13)
try:
    import mediapipe as mp
    if not hasattr(mp, 'solutions'):
        raise ImportError("mediapipe.solutions is missing")
    mp_face = mp.solutions.face_detection
    HAS_MEDIAPIPE = True
except (ImportError, AttributeError):
    mp_face = None
    HAS_MEDIAPIPE = False
    logging.warning("MediaPipe solutions not found or incompatible. Falling back to Center-Crop mode.")

logger = logging.getLogger(__name__)

CROP_W     = 608    # 9:16 output width at 1080p height
FRAME_SKIP = 10     # Run MediaPipe every N frames (optimized for Free tier speed)
SMOOTH_WIN = 30     # Rolling average window (frames)


def detect_face_centers(video_path: str) -> list[int]:
    """
    Detect face center X positions for every frame of the video.

    If MediaPipe is available, it runs every FRAME_SKIP frames and interpolates.
    If MediaPipe is missing, it returns the frame center for all frames (Fallback).
    """
    cap         = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    default_cx   = frame_w // 2

    # ── Fallback: Center-Crop ──────────────────────────────────────────────
    if not HAS_MEDIAPIPE:
        logger.info(f"Center-Crop Fallback: Producing {total_frames} centered frames.")
        cap.release()
        return [default_cx] * max(total_frames, 1)

    # ── Smart-Crop: MediaPipe ─────────────────────────────────────────────
    face_detector = mp_face.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.5,
    )

    cap         = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    default_cx   = frame_w // 2

    logger.info(
        f"Face tracking: {total_frames} frames @ frame_w={frame_w}px, "
        f"skip={FRAME_SKIP} → ~{total_frames // FRAME_SKIP} detections"
    )

    keyframe_indices: list[int]   = []
    keyframe_centers: list[float] = []

    frame_idx: int = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_SKIP == 0:
            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detector.process(rgb)

            if results.detections:
                bbox = results.detections[0].location_data.relative_bounding_box
                cx   = (bbox.xmin + bbox.width / 2) * frame_w
                # Clamp inside frame
                cx   = max(CROP_W / 2, min(float(cx), frame_w - CROP_W / 2))
            else:
                cx = float(default_cx)

            keyframe_indices.append(frame_idx)
            keyframe_centers.append(cx)

        frame_idx += 1

    cap.release()
    face_detector.close()

    if not keyframe_centers:
        logger.warning("No faces detected in video — using frame center throughout")
        return [default_cx] * max(total_frames, 1)

    # Interpolate between keyframes to fill every frame
    all_indices = np.arange(frame_idx)   # actual frame count
    interpolated = np.interp(all_indices, keyframe_indices, keyframe_centers)

    # 30-frame rolling average → smooth jitter
    smoothed = uniform_filter1d(interpolated, size=SMOOTH_WIN).astype(int)

    logger.info(f"Face tracking complete: {len(smoothed)} frames produced")
    return smoothed.tolist()


def get_crop_x(center_x: int, frame_w: int = 1920) -> int:
    """
    Convert face center X to the left edge of the 608px crop window.
    Clamped so the window never goes outside the frame.

    Args:
        center_x: Smoothed face center X pixel position.
        frame_w:  Total frame width in pixels.

    Returns:
        Left edge X of the crop window.
    """
    x = int(center_x - CROP_W / 2)
    return max(0, min(x, frame_w - CROP_W))
