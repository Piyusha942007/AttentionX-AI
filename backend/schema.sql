-- ============================================================
-- AttentionXAI — Supabase Schema
-- Run this in the Supabase SQL Editor to initialize your project.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ────────────────────────────────────────────────────────────
-- Table: jobs
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status        TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','transcribing','analyzing','cropping','done','failed')),
    filename      TEXT,
    video_url     TEXT,          -- Supabase Storage public URL of the uploaded video
    storage_path  TEXT,          -- Supabase Storage internal path (for downloading to local worker)
    peaks         JSONB,         -- Array of Peak objects once pipeline is done
    rms_array     JSONB,         -- Downsampled RMS float array for the frontend chart
    duration      FLOAT,         -- Video duration in seconds
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on every row change
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ────────────────────────────────────────────────────────────
-- Row-Level Security (RLS)
-- Using service role key in the backend bypasses RLS,
-- so these policies only matter for client-side access.
-- ────────────────────────────────────────────────────────────
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Allow anyone to read their job by ID (anon key)
CREATE POLICY "Public read by job id" ON jobs
    FOR SELECT USING (true);

-- Only service role can insert / update / delete
-- (Backend always uses SUPABASE_SERVICE_KEY — no policy needed for service role)

-- ────────────────────────────────────────────────────────────
-- Storage Buckets
-- Create these in the Supabase Dashboard → Storage  →  New Bucket
-- OR uncomment and run via the storage API after authenticating.
-- ────────────────────────────────────────────────────────────

-- Bucket 1: attentionx-videos  (private — only backend reads/writes)
-- Bucket 2: attentionx-clips   (public  — signed or public URLs for download)

-- Recommended bucket settings:
--   attentionx-videos  → Private, max file size 500 MB, allowed MIME: video/*
--   attentionx-clips   → Public,  max file size 200 MB, allowed MIME: video/mp4

-- ────────────────────────────────────────────────────────────
-- Index
-- ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);
