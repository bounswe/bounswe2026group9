-- 009: Atomic event creation via RPC
-- Wraps event + locations + categories + venue_metadata + equipment inserts in a single transaction.
-- Run this in Supabase SQL Editor.

CREATE OR REPLACE FUNCTION create_event_atomic(
    p_event JSONB,
    p_locations JSONB,
    p_categories JSONB,
    p_venue_metadata JSONB DEFAULT NULL,
    p_equipment JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_event_id UUID;
    v_event_row RECORD;
    v_result JSONB;
BEGIN
    -- Insert event
    INSERT INTO public.events (
        host_id, title, description, start_datetime, end_datetime,
        visibility, is_age_restricted, attendee_limit, status
    )
    SELECT
        (p_event->>'host_id')::UUID,
        p_event->>'title',
        p_event->>'description',
        (p_event->>'start_datetime')::TIMESTAMPTZ,
        (p_event->>'end_datetime')::TIMESTAMPTZ,
        p_event->>'visibility',
        (p_event->>'is_age_restricted')::BOOLEAN,
        (p_event->>'attendee_limit')::INTEGER,
        p_event->>'status'
    RETURNING id INTO v_event_id;

    -- Insert locations
    INSERT INTO public.event_locations (event_id, name, latitude, longitude, is_primary, order_index)
    SELECT
        v_event_id,
        loc->>'name',
        (loc->>'latitude')::DOUBLE PRECISION,
        (loc->>'longitude')::DOUBLE PRECISION,
        (loc->>'is_primary')::BOOLEAN,
        (loc->>'order_index')::INTEGER
    FROM jsonb_array_elements(p_locations) AS loc;

    -- Insert categories
    INSERT INTO public.event_categories (event_id, category_id)
    SELECT v_event_id, (cat->>'category_id')::UUID
    FROM jsonb_array_elements(p_categories) AS cat;

    -- Insert venue metadata (optional)
    IF p_venue_metadata IS NOT NULL THEN
        INSERT INTO public.venue_metadata (
            event_id, price, language, health_requirements, wheelchair_access, accessible_restroom,
            elevator_available, seating_available, captions_support, quiet_friendly
        ) VALUES (
            v_event_id,
            p_venue_metadata->>'price',
            p_venue_metadata->>'language',
            p_venue_metadata->>'health_requirements',
            (p_venue_metadata->>'wheelchair_access')::BOOLEAN,
            (p_venue_metadata->>'accessible_restroom')::BOOLEAN,
            (p_venue_metadata->>'elevator_available')::BOOLEAN,
            (p_venue_metadata->>'seating_available')::BOOLEAN,
            (p_venue_metadata->>'captions_support')::BOOLEAN,
            (p_venue_metadata->>'quiet_friendly')::BOOLEAN
        );
    END IF;

    -- Insert equipment requirements (optional)
    IF p_equipment IS NOT NULL THEN
        INSERT INTO public.equipment_requirements (event_id, item_name, is_required)
        SELECT
            v_event_id,
            eq->>'item_name',
            (eq->>'is_required')::BOOLEAN
        FROM jsonb_array_elements(p_equipment) AS eq;
    END IF;

    -- Return the created event
    SELECT to_jsonb(e) INTO v_result
    FROM public.events e
    WHERE e.id = v_event_id;

    RETURN v_result;
END;
$$;
