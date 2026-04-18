"""
captioner.py — Burn karaoke-style captions onto vertical clips via ffmpeg.

Uses the ASS (Advanced SubStation Alpha) subtitle format which natively
supports per-word karaoke highlight timing via {\k<centiseconds>} tags.

ASS is much more reliable than a chain of ffmpeg drawtext filters (which
can exceed shell argument length limits for long videos).

Caption style:
  - Active word:  Yellow (#FFE234), bold, pop-in scale effect
  - Sentence:     White, bold, black 3px outline
  - Position:     Bottom third of frame (y = 78% of height)
  - Font:         Arial 52pt (monospaced-safe substitute)
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

# Configure ffmpeg cross-platform
if os.name == "nt":
    BACKEND_DIR = Path(__file__).parent.parent
    FFMPEG_EXE = str(BACKEND_DIR / "ffmpeg.exe")
else:
    FFMPEG_EXE = "ffmpeg"

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output_clips"))

COLOR_MAP = {
    "Yellow": "&H0034E2FF", # Standard vibrant yellow
    "Green": "&H0000FF00",  # Bright Green
    "Cyan": "&H00FFFF00",   # Bright Cyan
    "Pink": "&H00FF00FF",   # Neon Pink
}

def get_ass_header(color_name: str) -> str:
    color_hex = COLOR_MAP.get(color_name, "&H0034E2FF")
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 608
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: White,Arial,48,&H00FFFFFF,{color_hex},&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,3,1,2,40,40,240,1
Style: Active,Arial,48,{color_hex},&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,105,105,0,0,1,3,1,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

WORDS_PER_LINE = 4   # Reduced chunks to fit safely within 9:16 boundaries


def _seconds_to_ass_time(t: float) -> str:
    """Convert seconds to ASS timestamp format H:MM:SS.cc"""
    t = max(0.0, t)
    h  = int(t // 3600)
    m  = int((t % 3600) // 60)
    s  = int(t % 60)
    cs = int(round((t % 1) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_ass_events(words: list[dict], clip_start: float) -> list[str]:
    """
    Build ASS Dialogue lines from word-level timestamps.

    Each sentence chunk produces:
      - One "White" dialogue line showing the full sentence for its duration
      - One "Active" karaoke line using {\\k} tags to highlight each word

    Args:
        words:       Flat word list [{"word": str, "start": float, "end": float}]
        clip_start:  Absolute video timestamp of the clip's start (seconds).
                     All word timestamps are shifted by -clip_start.

    Returns:
        List of ASS Dialogue line strings ready to be joined.
    """
    if not words:
        return []

    events: list[str] = []

    # Chunk words into sentence-sized lines
    chunks = [words[i: i + WORDS_PER_LINE] for i in range(0, len(words), WORDS_PER_LINE)]

    for chunk in chunks:
        # Relative timestamps (seconds from clip start)
        rel_start = chunk[0]["start"] - clip_start
        rel_end   = chunk[-1]["end"]  - clip_start

        # Skip chunks before the clip starts
        if rel_end < 0:
            continue

        rel_start = max(0.0, rel_start)
        t_start   = _seconds_to_ass_time(rel_start)
        t_end     = _seconds_to_ass_time(rel_end)

        # ── Full sentence in white (background layer) ─────────────────────
        sentence_text = " ".join(w["word"] for w in chunk)
        events.append(
            f"Dialogue: 0,{t_start},{t_end},White,,0,0,0,,"
            f"{sentence_text}"
        )

        # ── Karaoke active-word line ───────────────────────────────────────
        # {\\kN} = highlight this word for N centiseconds
        karaoke_parts: list[str] = []
        for w in chunk:
            w_dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
            karaoke_parts.append(f"{{\\k{w_dur_cs}}}{w['word']}")

        events.append(
            f"Dialogue: 1,{t_start},{t_end},Active,,0,0,0,,"
            + " ".join(karaoke_parts)
        )

    return events


def _write_ass_file(words: list[dict], clip_start: float, caption_color: str) -> str:
    """Write ASS subtitle file to a temp file and return its path."""
    events = _build_ass_events(words, clip_start)
    ass_content = get_ass_header(caption_color) + "\n".join(events) + "\n"

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ass", delete=False, encoding="utf-8"
    )
    tmp.write(ass_content)
    tmp.flush()
    tmp.close()
    return tmp.name


def burn_captions(
    clip_path:    str,
    words:        list[dict],
    clip_start:   float,
    output_path:  str,
    caption_color: str = "Yellow",
) -> str:
    """
    Burn karaoke-style captions onto a clip using ffmpeg ASS subtitles.

    Active word is highlighted depending on the caption_color.
    Falls back to returning the original uncaptioned clip if ffmpeg fails.

    Args:
        clip_path:     Path to the uncaptioned 9:16 MP4.
        words:         Word-level timestamps [{"word", "start", "end"}].
        clip_start:    Absolute start time of the clip in the source video.
        output_path:   Path for the captioned output MP4.
        caption_color: Color string matching the UI.

    Returns:
        Path to the captioned clip (or original clip if captioning fails).
    """
    if not words:
        logger.warning("No words supplied — skipping caption burn")
        return clip_path

    ass_path: str | None = None
    try:
        ass_path = _write_ass_file(words, clip_start, caption_color)
        logger.info(f"ASS subtitle file written: {ass_path} ({len(words)} words)")

        # FFMpeg's subtitle filter crashes on Windows absolute paths (C:\) because
        # ':' implies a filter chain link. We must swap slashes and escape the colon.
        ffmpeg_path = ass_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            FFMPEG_EXE, "-y",
            "-i", clip_path,
            "-vf", f"ass='{ffmpeg_path}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "copy",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(
                f"ffmpeg caption burn failed (rc={result.returncode}): "
                f"{result.stderr[-600:]}"
            )
            return clip_path

        logger.info(f"Captions burned → {output_path}")
        return output_path

    except Exception as exc:
        logger.error(f"Caption burn exception: {exc}", exc_info=True)
        return clip_path

    finally:
        # Clean up temp ASS file
        if ass_path:
            try:
                os.unlink(ass_path)
            except OSError:
                pass
