-- 014: Free-text review alongside star score (issue #230 / #235)
-- Adds an optional `review_text` column to the ratings table so attendees can
-- leave a written review next to their star score. Existing rows are
-- unaffected (review_text NULL).
--
-- Whitespace-only text is normalised to NULL in the service layer, so the DB
-- only sees actual text or NULL. Length is enforced by a CHECK constraint
-- (≤ 1000 chars) — Pydantic also enforces this at the request boundary,
-- but the DB constraint is the last line of defence.
--
-- Run this in the Supabase SQL Editor BEFORE deploying the matching backend
-- code, or every rating insert will fail (the request schema accepts
-- `review_text` but the column does not exist yet).

ALTER TABLE public.ratings
    ADD COLUMN IF NOT EXISTS review_text TEXT;

ALTER TABLE public.ratings
    DROP CONSTRAINT IF EXISTS ratings_review_text_length;
ALTER TABLE public.ratings
    ADD CONSTRAINT ratings_review_text_length
    CHECK (review_text IS NULL OR char_length(review_text) <= 1000);

-- Supports newest-first reviews-by-host pagination.
CREATE INDEX IF NOT EXISTS idx_ratings_host_created
    ON public.ratings (host_id, created_at DESC);
