"""
scorer.py — Audio energy extraction, signal fusion, and top-peak selection.

Implements the Viral Signal Algorithm from the PRD:
  Signal A (40%) — Librosa RMS audio energy
  Signal B (60%) — Gemini virality score
  Fusion         — weighted sum → ranked → top-5 non-overlapping clips
"""
import subprocess
import numpy as np

logger = logging.getLogger(__name__)

# Frontend chart: downsample the full RMS array to this many data points
CHART_POINTS = 500

# Clip output settings
DEFAULT_CLIP_DURATION = 60.0   # seconds — target clip length
MIN_GAP_BETWEEN_CLIPS = 90.0   # seconds — enforce gap between selected clips
TOP_N_CLIPS = 5

def extract_rms(video_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    STREAMS audio from video via FFmpeg to calculate RMS without high RAM usage.
    Replaces librosa.load which was causing OOM crashes.
    """
    logger.info(f"Streaming RMS extraction (Zero-RAM mode) from: {video_path}")
    
    # 1. Spawn FFmpeg to stream mono 16kHz float32 audio to stdout
    cmd = [
        "ffmpeg", "-i", video_path,
        "-f", "f32le", "-ac", "1", "-ar", "16000",
        "pipe:1"
    ]
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # 1 second of 16kHz audio = 16,000 floats * 4 bytes = 64,000 bytes
        chunk_size = 16000 * 4 
        rms_values = []
        
        while True:
            raw_data = proc.stdout.read(chunk_size)
            if not raw_data:
                break
            
            # Convert bytes to numpy array
            audio_chunk = np.frombuffer(raw_data, dtype=np.float32)
            if len(audio_chunk) == 0:
                break
                
            # Manual RMS calculation: sqrt(mean(x^2))
            rms = np.sqrt(np.mean(np.square(audio_chunk)) + 1e-9)
            rms_values.append(float(rms))
            
        proc.wait()
        
        if not rms_values:
            logger.warning("No audio data extracted; using zero-array")
            return np.array([0.0]), np.array([0.0])

        # 2. Normalize and Smooth (Native NumPy)
        energy = np.array(rms_values)
        energy_norm = (energy - energy.min()) / (energy.max() - energy.min() + 1e-9)
        
        # 20-sample rolling average
        energy_smooth = np.convolve(energy_norm, np.ones(20) / 20, mode="same")
        
        # Frame times: since each chunk is exactly 1 second (16kHz chunk_size)
        frame_times = np.arange(len(energy_smooth)).astype(float)
        
        logger.info(f"Streamed RMS: {len(energy_smooth)} seconds analyzed.")
        return frame_times, energy_smooth
        
    except Exception as e:
        logger.error(f"Streaming RMS failed: {e}")
        return np.array([0.0]), np.array([0.0])


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
