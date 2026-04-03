-- 010: Atomic event update via RPC
-- Wraps event update + delete/reinsert of locations, categories, venue_metadata, equipment in a single transaction.
-- Run this in Supabase SQL Editor.

CREATE OR REPLACE FUNCTION update_event_atomic(
    p_event_id UUID,
    p_event_data JSONB DEFAULT NULL,
    p_locations JSONB DEFAULT NULL,
    p_categories JSONB DEFAULT NULL,
    p_venue_metadata JSONB DEFAULT NULL,
    p_equipment JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
    v_key TEXT;
    v_update_sql TEXT := '';
    v_first BOOLEAN := TRUE;
BEGIN
    -- Update event fields (dynamic based on provided keys)
    IF p_event_data IS NOT NULL AND p_event_data != '{}'::JSONB THEN
        v_update_sql := 'UPDATE public.events SET ';
        FOR v_key IN SELECT jsonb_object_keys(p_event_data) LOOP
            IF NOT v_first THEN
                v_update_sql := v_update_sql || ', ';
            END IF;
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

    -- Replace locations
    IF p_locations IS NOT NULL THEN
        DELETE FROM public.event_locations WHERE event_id = p_event_id;
        INSERT INTO public.event_locations (event_id, name, latitude, longitude, is_primary, order_index)
        SELECT
            p_event_id,
            loc->>'name',
            (loc->>'latitude')::DOUBLE PRECISION,
            (loc->>'longitude')::DOUBLE PRECISION,
            (loc->>'is_primary')::BOOLEAN,
            (loc->>'order_index')::INTEGER
        FROM jsonb_array_elements(p_locations) AS loc;
    END IF;

    -- Replace categories
    IF p_categories IS NOT NULL THEN
        DELETE FROM public.event_categories WHERE event_id = p_event_id;
        INSERT INTO public.event_categories (event_id, category_id)
        SELECT p_event_id, (cat->>'category_id')::UUID
        FROM jsonb_array_elements(p_categories) AS cat;
    END IF;

    -- Replace venue metadata
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

    -- Replace equipment
    IF p_equipment IS NOT NULL THEN
        DELETE FROM public.equipment_requirements WHERE event_id = p_event_id;
        INSERT INTO public.equipment_requirements (event_id, item_name, is_required)
        SELECT
            p_event_id,
            eq->>'item_name',
            (eq->>'is_required')::BOOLEAN
        FROM jsonb_array_elements(p_equipment) AS eq;
    END IF;

    -- Return updated event
    SELECT to_jsonb(e) INTO v_result
    FROM public.events e
    WHERE e.id = p_event_id;

    RETURN v_result;
END;
$$;
