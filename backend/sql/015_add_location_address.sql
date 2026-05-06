-- 015: Add location_address text field to event_locations
-- Stores a human-readable address (reverse-geocoded from lat/lng) alongside coordinates.
-- Run this in Supabase SQL Editor.

ALTER TABLE public.event_locations
    ADD COLUMN IF NOT EXISTS location_address TEXT;

-- Update both atomic RPCs to include location_address in their location INSERT statements.
-- This is a minimal re-statement of 013_atomic_event_rpc_segments.sql with the added field.

CREATE OR REPLACE FUNCTION create_event_atomic(
    p_event JSONB,
    p_locations JSONB,
    p_categories JSONB,
    p_venue_metadata JSONB DEFAULT NULL,
    p_equipment JSONB DEFAULT NULL,
    p_segments JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_event_id UUID;
    v_result JSONB;
    v_location_ids UUID[] := ARRAY[]::UUID[];
    v_loc_count INT;
    v_segment_location_id UUID;
    v_seg JSONB;
    v_loc JSONB;
    v_inserted_id UUID;
    v_loc_idx INT;
BEGIN
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

    FOR v_loc IN
        SELECT loc FROM jsonb_array_elements(p_locations) WITH ORDINALITY AS t(loc, ord) ORDER BY ord
    LOOP
        INSERT INTO public.event_locations (
            event_id, name, latitude, longitude, is_primary, order_index, location_address
        ) VALUES (
            v_event_id,
            v_loc->>'name',
            (v_loc->>'latitude')::DOUBLE PRECISION,
            (v_loc->>'longitude')::DOUBLE PRECISION,
            (v_loc->>'is_primary')::BOOLEAN,
            (v_loc->>'order_index')::INTEGER,
            v_loc->>'location_address'
        )
        RETURNING id INTO v_inserted_id;
        v_location_ids := array_append(v_location_ids, v_inserted_id);
    END LOOP;

    v_loc_count := COALESCE(array_length(v_location_ids, 1), 0);

    INSERT INTO public.event_categories (event_id, category_id)
    SELECT v_event_id, (cat->>'category_id')::UUID
    FROM jsonb_array_elements(p_categories) AS cat;

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

    IF p_equipment IS NOT NULL THEN
        INSERT INTO public.equipment_requirements (event_id, item_name, is_required)
        SELECT v_event_id, eq->>'item_name', (eq->>'is_required')::BOOLEAN
        FROM jsonb_array_elements(p_equipment) AS eq;
    END IF;

    IF p_segments IS NOT NULL AND jsonb_array_length(p_segments) > 0 THEN
        FOR v_seg IN SELECT * FROM jsonb_array_elements(p_segments) LOOP
            v_loc_idx := (v_seg->>'location_index')::INT;
            IF v_loc_idx < 0 OR v_loc_idx >= v_loc_count THEN
                RAISE EXCEPTION 'segment.location_index % out of range', v_loc_idx
                    USING ERRCODE = 'check_violation';
            END IF;
            v_segment_location_id := v_location_ids[v_loc_idx + 1];
            INSERT INTO public.event_segments (
                event_id, location_id, order_index, start_datetime, end_datetime, description
            ) VALUES (
                v_event_id, v_segment_location_id,
                (v_seg->>'order_index')::INT,
                (v_seg->>'start_datetime')::TIMESTAMPTZ,
                (v_seg->>'end_datetime')::TIMESTAMPTZ,
                v_seg->>'description'
            );
        END LOOP;
    END IF;

    SELECT to_jsonb(e) INTO v_result FROM public.events e WHERE e.id = v_event_id;
    RETURN v_result;
END;
$$;


CREATE OR REPLACE FUNCTION update_event_atomic(
    p_event_id UUID,
    p_event_data JSONB DEFAULT NULL,
    p_locations JSONB DEFAULT NULL,
    p_categories JSONB DEFAULT NULL,
    p_venue_metadata JSONB DEFAULT NULL,
    p_equipment JSONB DEFAULT NULL,
    p_segments JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
    v_key TEXT;
    v_update_sql TEXT := '';
    v_first BOOLEAN := TRUE;
    v_location_ids UUID[];
    v_loc_count INT;
    v_segment_location_id UUID;
    v_seg JSONB;
    v_loc JSONB;
    v_inserted_id UUID;
    v_loc_idx INT;
BEGIN
    IF p_event_data IS NOT NULL AND p_event_data != '{}'::JSONB THEN
        v_update_sql := 'UPDATE public.events SET ';
        FOR v_key IN SELECT jsonb_object_keys(p_event_data) LOOP
            IF NOT v_first THEN v_update_sql := v_update_sql || ', '; END IF;
            v_first := FALSE;
            CASE v_key
                WHEN 'start_datetime', 'end_datetime' THEN
                    v_update_sql := v_update_sql || v_key || ' = (' || quote_literal(p_event_data->>v_key) || ')::TIMESTAMPTZ';
                WHEN 'is_age_restricted' THEN
                    v_update_sql := v_update_sql || v_key || ' = (' || quote_literal(p_event_data->>v_key) || ')::BOOLEAN';
                WHEN 'attendee_limit' THEN
                    IF p_event_data->>v_key IS NULL THEN
                        v_update_sql := v_update_sql || v_key || ' = NULL';
                    ELSE
                        v_update_sql := v_update_sql || v_key || ' = (' || quote_literal(p_event_data->>v_key) || ')::INTEGER';
                    END IF;
                ELSE
                    v_update_sql := v_update_sql || v_key || ' = ' || quote_literal(p_event_data->>v_key);
            END CASE;
        END LOOP;
        v_update_sql := v_update_sql || ' WHERE id = ' || quote_literal(p_event_id);
        EXECUTE v_update_sql;
    END IF;

    IF p_locations IS NOT NULL THEN
        DELETE FROM public.event_locations WHERE event_id = p_event_id;
        v_location_ids := ARRAY[]::UUID[];
        FOR v_loc IN
            SELECT loc FROM jsonb_array_elements(p_locations) WITH ORDINALITY AS t(loc, ord) ORDER BY ord
        LOOP
            INSERT INTO public.event_locations (
                event_id, name, latitude, longitude, is_primary, order_index, location_address
            ) VALUES (
                p_event_id,
                v_loc->>'name',
                (v_loc->>'latitude')::DOUBLE PRECISION,
                (v_loc->>'longitude')::DOUBLE PRECISION,
                (v_loc->>'is_primary')::BOOLEAN,
                (v_loc->>'order_index')::INTEGER,
                v_loc->>'location_address'
            )
            RETURNING id INTO v_inserted_id;
            v_location_ids := array_append(v_location_ids, v_inserted_id);
        END LOOP;
    END IF;

    IF p_categories IS NOT NULL THEN
        DELETE FROM public.event_categories WHERE event_id = p_event_id;
        INSERT INTO public.event_categories (event_id, category_id)
        SELECT p_event_id, (cat->>'category_id')::UUID
        FROM jsonb_array_elements(p_categories) AS cat;
    END IF;

    IF p_venue_metadata IS NOT NULL THEN
        DELETE FROM public.venue_metadata WHERE event_id = p_event_id;
        INSERT INTO public.venue_metadata (
            event_id, price, language, health_requirements, wheelchair_access, accessible_restroom,
            elevator_available, seating_available, captions_support, quiet_friendly
        ) VALUES (
            p_event_id,
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

    IF p_equipment IS NOT NULL THEN
        DELETE FROM public.equipment_requirements WHERE event_id = p_event_id;
        INSERT INTO public.equipment_requirements (event_id, item_name, is_required)
        SELECT p_event_id, eq->>'item_name', (eq->>'is_required')::BOOLEAN
        FROM jsonb_array_elements(p_equipment) AS eq;
    END IF;

    IF p_segments IS NOT NULL THEN
        DELETE FROM public.event_segments WHERE event_id = p_event_id;
        IF jsonb_array_length(p_segments) > 0 THEN
            IF v_location_ids IS NULL THEN
                SELECT array_agg(id ORDER BY created_at, order_index, id)
                INTO v_location_ids
                FROM public.event_locations
                WHERE event_id = p_event_id;
            END IF;
            v_loc_count := COALESCE(array_length(v_location_ids, 1), 0);
            IF v_loc_count = 0 THEN
                RAISE EXCEPTION 'cannot insert segments: event has no locations'
                    USING ERRCODE = 'check_violation';
            END IF;
            FOR v_seg IN SELECT * FROM jsonb_array_elements(p_segments) LOOP
                v_loc_idx := (v_seg->>'location_index')::INT;
                IF v_loc_idx < 0 OR v_loc_idx >= v_loc_count THEN
                    RAISE EXCEPTION 'segment.location_index % out of range', v_loc_idx
                        USING ERRCODE = 'check_violation';
                END IF;
                v_segment_location_id := v_location_ids[v_loc_idx + 1];
                INSERT INTO public.event_segments (
                    event_id, location_id, order_index, start_datetime, end_datetime, description
                ) VALUES (
                    p_event_id, v_segment_location_id,
                    (v_seg->>'order_index')::INT,
                    (v_seg->>'start_datetime')::TIMESTAMPTZ,
                    (v_seg->>'end_datetime')::TIMESTAMPTZ,
                    v_seg->>'description'
                );
            END LOOP;
        END IF;
    END IF;

    SELECT to_jsonb(e) INTO v_result FROM public.events e WHERE e.id = p_event_id;
    RETURN v_result;
END;
$$;
