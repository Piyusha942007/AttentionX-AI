"""
analyzer.py — Gemini 1.5 Flash virality analysis of transcript segments.

Chunks the transcript into ~2-minute windows, sends each to Gemini with
the virality scoring prompt, parses the JSON response, and returns a flat
list of candidate viral peaks.

Edge case: if Gemini returns malformed JSON, the call is retried once
with response_mime_type="application/json" (Gemini constrained decoding).
"""
from __future__ import annotations

import json
import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

_VIRALITY_SYSTEM_PROMPT = """You are a viral short-form content analyst specializing in TikTok, Instagram Reels, and YouTube Shorts.

Given a timestamped transcript excerpt, identify the moments most likely to go viral as standalone 45–60 second vertical clips.

Return a JSON array. Each element must be an object with EXACTLY these keys:
{
  "start":          <float — timestamp in seconds where the clip should begin>,
  "end":            <float — timestamp in seconds where the clip should end (min 45s after start)>,
  "virality_score": <float 0.0–1.0 — how viral this moment would be as a standalone clip>,
  "reason":         <one of: "profound_insight" | "personal_story" | "surprising_stat" | "actionable_tip" | "emotional_peak" | "counterintuitive_claim" | "quotable_one_liner">,
  "hook_headline":  <string — 5 to 8 word scroll-stopping hook (no hashtags, no emojis)>,
  "clip_title":     <string — 3 to 5 word clip title>
}

Score HIGHEST for:
- Personal vulnerability and raw, honest confessions
- Counterintuitive or surprising claims that challenge assumptions
- Actionable frameworks with clear, repeatable steps
- Quotable one-liners people will screenshot and share
- Emotional peaks: turning-point stories, epiphany moments

Score LOWER for:
- Generic advice ("work hard", "believe in yourself")
- Transitions, intros, or off-topic segments
- Moments heavily reliant on visual context

Return ONLY the JSON array — no markdown, no explanation, no code fences.
If no suitable moment exists, return an empty array: []

TRANSCRIPT:
"""

_CHUNK_DURATION = 120.0  # seconds per chunk


# ─────────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_transcript(segments: list[dict]) -> list[tuple[float, float, str]]:
    """
    Split transcript segments into ~2-minute text chunks.

    Returns:
        List of (chunk_start, chunk_end, formatted_text) tuples.
    """
    if not segments:
        return []

    chunks: list[tuple[float, float, str]] = []
    chunk_start = segments[0]["start"]
    chunk_end   = chunk_start
    lines: list[str] = []

    for seg in segments:
        # Flush when chunk exceeds target duration
        if seg["start"] - chunk_start >= _CHUNK_DURATION and lines:
            chunks.append((chunk_start, chunk_end, "\n".join(lines)))
            chunk_start = seg["start"]
            lines = []

        lines.append(f"[{seg['start']:.1f}s] {seg['text']}")
        chunk_end = seg["end"]

    if lines:
        chunks.append((chunk_start, chunk_end, "\n".join(lines)))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Gemini call
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini(text: str, *, force_json_mime: bool = False) -> list[dict]:
    """
    Send a transcript chunk to Gemini and parse the JSON response.

    Args:
        text:            The timestamped transcript text.
        force_json_mime: If True, uses response_mime_type="application/json"
                         (constrained decoding — retry path).

    Returns:
        List of candidate peak dicts from Gemini.
    """
    kwargs: dict = {"temperature": 0.2}
    if force_json_mime:
        kwargs["response_mime_type"] = "application/json"

    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config=kwargs,
    )

    response = model.generate_content(_VIRALITY_SYSTEM_PROMPT + text)
    raw = response.text.strip()

    # Strip markdown code fences if Gemini wrapped the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        # Sometimes Gemini wraps the array in an object
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []
    except json.JSONDecodeError:
        return []


def _safe_call_gemini(text: str, chunk_label: str) -> list[dict]:
    """
    Call Gemini with automatic retry on JSON parse failure.
    """
    peaks = _call_gemini(text, force_json_mime=False)
    if not peaks:
        logger.warning(f"{chunk_label}: Gemini returned no peaks, retrying with JSON MIME…")
        peaks = _call_gemini(text, force_json_mime=True)
    return peaks


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def analyze_transcript(segments: list[dict]) -> list[dict]:
    """
    Send transcript chunks to Gemini and collect candidate viral peaks.

    Args:
        segments: Whisper segment list (from transcriber.transcribe_video).

    Returns:
        Flat list of candidate peak dicts.  Each dict has:
          start, end, gemini_score, reason, headline, clip_title
    """
    chunks = _chunk_transcript(segments)
    logger.info(f"Analyzing {len(chunks)} transcript chunks with Gemini…")

    all_peaks: list[dict] = []

    for i, (c_start, c_end, text) in enumerate(chunks):
        label = f"Chunk {i + 1}/{len(chunks)} ({c_start:.0f}s–{c_end:.0f}s)"
        logger.info(f"  {label}")

        try:
            raw_peaks = _safe_call_gemini(text, label)
            for p in raw_peaks:
                all_peaks.append({
                    "start":        float(p.get("start",          c_start)),
                    "end":          float(p.get("end",            c_end)),
                    "gemini_score": float(p.get("virality_score", 0.5)),
                    "reason":       str(p.get("reason",           "")),
                    "headline":     str(p.get("hook_headline",    "")),
                    "clip_title":   str(p.get("clip_title",       "")),
                })
        except Exception as exc:
            logger.error(f"  {label} failed: {exc}")

    logger.info(f"Gemini found {len(all_peaks)} candidate peaks across {len(chunks)} chunks")
    return all_peaks
