"""
models.py — Pydantic data models for AttentionXAI.
These define the Integration Contract shape shared between frontend and backend.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    queued       = "queued"
    downloading  = "downloading"
    transcribing = "transcribing"
    analyzing    = "analyzing"
    cropping     = "cropping"
    done         = "done"
    failed       = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────────────────

class WordTimestamp(BaseModel):
    """Single word with its start/end timestamps from Whisper."""
    word:  str
    start: float
    end:   float


class Peak(BaseModel):
    """
    A detected viral moment.  This is the primary unit of output from the
    AI pipeline, and the primary unit of input for the video crop engine.
    """
    # Timeline display
    time:       float = Field(..., description="Midpoint timestamp (seconds)")
    start:      float = Field(..., description="Clip start timestamp (seconds)")
    end:        float = Field(..., description="Clip end timestamp (seconds)")

    # Scores
    score:      float = Field(..., ge=0.0, le=1.0, description="Fused virality score 0–1")

    # Content metadata from Gemini
    headline:   str   = Field(default="", description="5–8 word scroll-stopping hook")
    clip_title: str   = Field(default="", description="Short clip title")
    reason:     str   = Field(default="", description="Why this moment is viral")

    # Clip output
    clip_id:    str   = Field(default="", description="UUID of the processed clip")
    clip_url:   str   = Field(default="", description="Supabase public URL of the final MP4")

    # Caption data
    words: list[WordTimestamp] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# API Response / Contract
# ─────────────────────────────────────────────────────────────────────────────

class JobCreateResponse(BaseModel):
    """Returned immediately after POST /api/jobs."""
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    """
    Full job object — the Integration Contract the frontend polls.

    Shape matches PRD spec:
    {
      "job_id": "uuid",
      "status": "queued|transcribing|analyzing|cropping|done|failed",
      "peaks": [...],
      "rms_array": [0.1, 0.3, ...],
      "duration": 3612.0
    }
    """
    job_id:        str
    status:        JobStatus
    filename:      str              = ""
    peaks:         list[Peak]       = Field(default_factory=list)
    rms_array:     list[float]      = Field(default_factory=list)
    duration:      float            = 0.0
    error_message: Optional[str]    = None
    created_at:    str              = ""
