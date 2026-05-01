-- 012: Itinerary segments for multi-location events
-- Each segment ties a single event_locations row to a time window with optional description.
-- Segments are optional — events without segments continue to work unchanged (backward compatible).
-- Run this in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS public.event_segments (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id       UUID        NOT NULL REFERENCES public.events(id)          ON DELETE CASCADE,
    location_id    UUID        NOT NULL REFERENCES public.event_locations(id) ON DELETE CASCADE,
    order_index    INT         NOT NULL,
    start_datetime TIMESTAMPTZ NOT NULL,
    end_datetime   TIMESTAMPTZ NOT NULL,
    description    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT segment_end_after_start CHECK (end_datetime > start_datetime),
    CONSTRAINT segment_order_unique    UNIQUE (event_id, order_index)
);

CREATE INDEX IF NOT EXISTS idx_event_segments_event_id ON public.event_segments (event_id, order_index);
CREATE INDEX IF NOT EXISTS idx_event_segments_location ON public.event_segments (location_id);
