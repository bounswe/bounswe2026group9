-- 016: Accent-insensitive text search for events (title, description, location name)
-- Enables unaccent extension and creates a helper function used by the backend
-- to find event IDs matching a search term regardless of accents/diacritics
-- (e.g. "besiktas" matches "Beşiktaş", "istanbull" matches "İstanbul").
--
-- Run this in Supabase SQL Editor.

CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION search_events_text(search_term TEXT)
RETURNS TABLE(event_id UUID)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    norm TEXT;
BEGIN
    -- Normalize: strip accents + lowercase on both sides
    norm := unaccent(lower(search_term));

    -- Match by event title or description
    RETURN QUERY
    SELECT DISTINCT e.id
    FROM public.events e
    WHERE unaccent(lower(e.title)) LIKE '%' || norm || '%'
       OR unaccent(lower(COALESCE(e.description, ''))) LIKE '%' || norm || '%';

    -- Match by location name
    RETURN QUERY
    SELECT DISTINCT el.event_id
    FROM public.event_locations el
    WHERE unaccent(lower(el.name)) LIKE '%' || norm || '%';
END;
$$;
