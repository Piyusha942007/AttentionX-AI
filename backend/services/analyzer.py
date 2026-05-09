"""
analyzer.py — Gemini 1.5 Flash virality analysis of transcript segments.

Chunks the transcript into ~2-minute windows, sends each to Gemini with
the virality scoring prompt, parses the JSON response, and returns a flat
list of candidate viral peaks.

Edge case: if Gemini returns malformed JSON, the call is retried once
with response_mime_type="application/json" (Gemini constrained decoding).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the new SDK client
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

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

def _format_full_transcript(segments: list[dict]) -> str:
    """Format the entire transcript for a single AI pass."""
    return "\n".join([f"[{seg['start']:.1f}s] {seg['text']}" for seg in segments])


# ─────────────────────────────────────────────────────────────────────────────
# Gemini call
# ─────────────────────────────────────────────────────────────────────────────

async def _call_gemini(text: str, *, force_json_mime: bool = False) -> list[dict]:
    """
    Send a transcript chunk to Gemini and parse the JSON response.
    """
    config = {
        "temperature": 0.2,
        "system_instruction": _VIRALITY_SYSTEM_PROMPT
    }
    
    if force_json_mime:
        config["response_mime_type"] = "application/json"

    try:
        # Using gemini-flash-latest: Resolves 404 issue in this environment
        response = await client.aio.models.generate_content(
            model="gemini-flash-latest", 
            contents=text,
            config=config,
        )
        
        if force_json_mime and response.parsed:
             return response.parsed if isinstance(response.parsed, list) else []

        raw = response.text.strip()

        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return []

async def _safe_call_gemini(text: str, chunk_label: str) -> list[dict]:
    """
    Call Gemini with automatic retry on JSON parse failure.
    """
    peaks = await _call_gemini(text, force_json_mime=False)
    if not peaks:
        logger.warning(f"{chunk_label}: Gemini returned no peaks, retrying with JSON MIME…")
        peaks = await _call_gemini(text, force_json_mime=True)
    return peaks


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

async def analyze_transcript(segments: list[dict]) -> list[dict]:
    """
    Send the ENTIRE transcript to Gemini in a single pass for maximum speed.
    """
    if not segments: return []
    
    full_text = _format_full_transcript(segments)
    logger.info("Analyzing FULL transcript with Gemini Flash (Ultra-Fast Mode)...")

    raw_peaks = await _safe_call_gemini(full_text, "Full Transcript")

    all_peaks: list[dict] = []
    for p in raw_peaks:
        all_peaks.append({
            "start":        float(p.get("start",          0)),
            "end":          float(p.get("end",            0)),
            "gemini_score": float(p.get("virality_score", 0.5)),
            "reason":       (p.get("reason") or "profound_insight").strip(),
            "headline":     (p.get("hook_headline") or "Viral Moment").strip(),
            "clip_title":   (p.get("clip_title") or "Nugget").strip(),
        })

    logger.info(f"Gemini found {len(all_peaks)} candidate peaks in a single pass.")
    return all_peaks
