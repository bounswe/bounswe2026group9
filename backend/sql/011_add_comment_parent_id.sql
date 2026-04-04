-- 011: Add parent_id to comments for nested replies
-- Run this in Supabase SQL Editor.

ALTER TABLE public.comments
    ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES public.comments(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON public.comments(parent_id);
