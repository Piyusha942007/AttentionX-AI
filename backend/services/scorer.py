"""
scorer.py — Audio energy extraction, signal fusion, and top-peak selection.

Implements the Viral Signal Algorithm from the PRD:
  Signal A (40%) — Librosa RMS audio energy
  Signal B (60%) — Gemini virality score
  Fusion         — weighted sum → ranked → top-5 non-overlapping clips
"""
from __future__ import annotations

import logging

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Frontend chart: downsample the full RMS array to this many data points
CHART_POINTS = 500

# Clip output settings
DEFAULT_CLIP_DURATION = 60.0   # seconds — target clip length
MIN_GAP_BETWEEN_CLIPS = 90.0   # seconds — enforce gap between selected clips
TOP_N_CLIPS = 5


# ─────────────────────────────────────────────────────────────────────────────
# Signal A — Audio Energy (Librosa)
# ─────────────────────────────────────────────────────────────────────────────

def extract_rms(video_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract and smooth RMS energy from a video/audio file.

    Pipeline:
      1. Librosa loads audio (mono, native sr)
      2. Compute RMS per frame (2048 window, 512 hop)
      3. Normalize to [0, 1]
      4. Apply 20-sample rolling average to reduce noise

    Returns:
        (frame_times, energy_smooth) — both np.ndarray of equal length.
        frame_times: timestamp (seconds) for each RMS frame.
        energy_smooth: smoothed, normalized RMS value per frame.
    """
    logger.info(f"Extracting audio RMS from: {video_path}")
    y, sr = librosa.load(video_path, mono=True)

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]

    # Normalize 0–1
    rms_min, rms_max = rms.min(), rms.max()
    rms_norm = (rms - rms_min) / (rms_max - rms_min + 1e-9)

    # Smooth with 20-sample rolling average (PRD spec)
    energy_smooth = np.convolve(rms_norm, np.ones(20) / 20, mode="same")

    frame_times = librosa.frames_to_time(
        np.arange(len(rms_norm)), sr=sr, hop_length=512
    )

    logger.info(
        f"RMS extracted: {len(energy_smooth)} frames, "
        f"audio duration {frame_times[-1]:.1f}s"
    )
    return frame_times, energy_smooth


def _audio_score_for_window(
    t_start: float,
    t_end: float,
    frame_times: np.ndarray,
    energy_smooth: np.ndarray,
) -> float:
    """Mean smoothed RMS energy in the time window [t_start, t_end]."""
    mask = (frame_times >= t_start) & (frame_times <= t_end)
    if not mask.any():
        return 0.0
    return float(np.mean(energy_smooth[mask]))


# ─────────────────────────────────────────────────────────────────────────────
# Fusion (PRD spec: 40% audio + 60% Gemini)
# ─────────────────────────────────────────────────────────────────────────────

def fuse_and_rank(
    candidate_peaks: list[dict],
    frame_times: np.ndarray,
    energy_smooth: np.ndarray,
) -> list[dict]:
    """
    Apply weighted fusion to each candidate peak and sort by virality_score.

    virality_score = 0.4 * audio_score + 0.6 * gemini_score

    Args:
        candidate_peaks: Output of analyzer.analyze_transcript().
        frame_times:     From extract_rms() — timestamp per RMS frame.
        energy_smooth:   From extract_rms() — smoothed RMS per frame.

    Returns:
        Peaks sorted by virality_score descending.
    """
    fused: list[dict] = []

    for peak in candidate_peaks:
        t_start = peak["start"]
        t_end   = peak["end"]

        audio_score  = _audio_score_for_window(t_start, t_end, frame_times, energy_smooth)
        gemini_score = peak.get("gemini_score", 0.5)

        virality_score = round(0.4 * audio_score + 0.6 * gemini_score, 4)

        fused.append({
            **peak,
            "audio_score":    round(audio_score,  4),
            "virality_score": virality_score,
            "time":           round((t_start + t_end) / 2, 2),  # midpoint for timeline
        })

    fused.sort(key=lambda p: p["virality_score"], reverse=True)
    logger.info(f"Fused {len(fused)} peaks; top score: {fused[0]['virality_score'] if fused else 'n/a'}")
    return fused


# ─────────────────────────────────────────────────────────────────────────────
# Selection — Top N non-overlapping clips
# ─────────────────────────────────────────────────────────────────────────────

def pick_top_peaks(
    ranked_peaks: list[dict],
    n: int = TOP_N_CLIPS,
    min_gap: float = MIN_GAP_BETWEEN_CLIPS,
    target_duration: float = DEFAULT_CLIP_DURATION,
) -> list[dict]:
    """
    Select the top N peaks with at least min_gap seconds between clips.

    Each selected peak is extended to target_duration if shorter.
    Clips are returned in chronological order.

    Args:
        ranked_peaks:    Output of fuse_and_rank() — sorted best-first.
        n:               Maximum number of clips to select (default 5).
        min_gap:         Minimum gap between clip end and next clip start (90s).
        target_duration: Desired clip length in seconds (60s).

    Returns:
        List of selected peak dicts sorted by start time.
    """
    selected: list[dict] = []

    for peak in ranked_peaks:
        if len(selected) >= n:
            break

        start = float(peak["start"])
        end   = float(peak["end"])

        # Extend short segments to target_duration
        duration = end - start
        if duration < target_duration:
            pad   = (target_duration - duration) / 2
            start = max(0.0, start - pad)
            end   = end + pad

        # Check min_gap constraint against all already-selected clips
        conflict = any(
            not (end + min_gap <= sel["start"] or start >= sel["end"] + min_gap)
            for sel in selected
        )
        if conflict:
            continue

        selected.append({**peak, "start": round(start, 2), "end": round(end, 2)})

    # Return in chronological order
    selected.sort(key=lambda p: p["start"])
    logger.info(f"Selected {len(selected)} non-overlapping clips (target={n}, min_gap={min_gap}s)")
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# Chart data helper
# ─────────────────────────────────────────────────────────────────────────────

def downsample_rms(energy_smooth: np.ndarray, n_points: int = CHART_POINTS) -> list[float]:
    """
    Downsample the full RMS array to n_points for the recharts BarChart.

    Uses uniform index sampling rather than averaging to preserve spike shape.
    """
    total = len(energy_smooth)
    if total <= n_points:
        return [round(float(v), 4) for v in energy_smooth]

    indices = np.linspace(0, total - 1, n_points, dtype=int)
    return [round(float(energy_smooth[i]), 4) for i in indices]
