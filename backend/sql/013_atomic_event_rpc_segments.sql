-- 013: Extend atomic event RPCs to insert/replace itinerary segments
-- Replaces 009_atomic_event_rpc.sql and 010_atomic_event_update_rpc.sql:
--   - adds optional p_segments JSONB parameter to both RPCs
--   - resolves each segment's location by *request-array position*
--     (the index that the client sees when reading p_locations[i])
--
-- Why the explicit FOR loop?
--   The client's SegmentRequest.location_index = "the i in locations[i]".
--   `INSERT ... SELECT ... ORDER BY ... RETURNING id` does NOT officially
--   guarantee that RETURNING yields rows in SELECT order — only that it
--   returns one row per inserted row. We therefore insert locations one
--   at a time, in request order, and accumulate the resulting UUIDs into
--   v_location_ids[]. This keeps the contract `v_location_ids[i+1] ==
--   id of p_locations[i]` rock solid.
--
--   On update, when only segments are sent (no locations), v_location_ids
--   is populated from existing rows ordered (created_at, order_index, id).
--   That ORDER BY is mirrored in app/repositories/event.py::get_event_locations
--   so the client's `location_index` references the same positional list
--   it just read from GET /events/{id}.
--
-- Backward compatible: passing NULL or omitting p_segments behaves exactly
-- like 009/010 — no segments are inserted.
--
-- Run this in the Supabase SQL Editor AFTER 012_create_event_segments.sql.

-- ----------------------------------------------------------------
-- Drop the legacy 5-parameter signatures from migrations 009/010 first.
-- `CREATE OR REPLACE FUNCTION` only replaces a function with an *identical*
-- parameter list — adding p_segments produces a new overload alongside the
-- old one, and PostgREST then errors out with PGRST203 on every RPC call
-- ("could not choose the best candidate"). Dropping the legacy signatures
-- here keeps the namespace unambiguous; the Python wrappers always send
-- the full 6-key payload (p_segments included, possibly NULL).
-- Safe to re-run: the IF EXISTS clauses turn this into a no-op when the
-- legacy signatures are already gone.
-- ----------------------------------------------------------------

DROP FUNCTION IF EXISTS public.create_event_atomic(jsonb, jsonb, jsonb, jsonb, jsonb);
DROP FUNCTION IF EXISTS public.update_event_atomic(uuid, jsonb, jsonb, jsonb, jsonb, jsonb);

-- ----------------------------------------------------------------
-- create_event_atomic
-- ----------------------------------------------------------------

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

    -- Insert locations one at a time, in request order, capturing the
    -- resulting UUIDs into v_location_ids. v_location_ids[i+1] then
    -- corresponds to p_locations[i] (PL/pgSQL arrays are 1-indexed).
    FOR v_loc IN
        SELECT loc FROM jsonb_array_elements(p_locations) WITH ORDINALITY AS t(loc, ord) ORDER BY ord
    LOOP
        INSERT INTO public.event_locations (
            event_id, name, latitude, longitude, is_primary, order_index
        ) VALUES (
            v_event_id,
            v_loc->>'name',
            (v_loc->>'latitude')::DOUBLE PRECISION,
            (v_loc->>'longitude')::DOUBLE PRECISION,
            (v_loc->>'is_primary')::BOOLEAN,
            (v_loc->>'order_index')::INTEGER
        )
        RETURNING id INTO v_inserted_id;
        v_location_ids := array_append(v_location_ids, v_inserted_id);
    END LOOP;

    v_loc_count := COALESCE(array_length(v_location_ids, 1), 0);

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

    -- Insert segments (optional). location_index is 0-based into the
    -- request's locations array; v_location_ids is 1-based, so add 1.
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
                v_event_id,
                v_segment_location_id,
                (v_seg->>'order_index')::INT,
                (v_seg->>'start_datetime')::TIMESTAMPTZ,
                (v_seg->>'end_datetime')::TIMESTAMPTZ,
                v_seg->>'description'
            );
        END LOOP;
    END IF;

    -- Return the created event
    SELECT to_jsonb(e) INTO v_result
    FROM public.events e
    WHERE e.id = v_event_id;

    RETURN v_result;
END;
$$;


-- ----------------------------------------------------------------
-- update_event_atomic
-- ----------------------------------------------------------------

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
    -- Note: deleting locations cascades to event_segments.location_id, so when
    -- p_locations is provided, any existing segments that referenced the old
    -- locations are wiped. Callers must therefore re-send segments alongside
    -- locations on update if they want to keep them. Same per-row insert
    -- pattern as create_event_atomic to anchor request-array positions to
    -- v_location_ids deterministically.
    IF p_locations IS NOT NULL THEN
        DELETE FROM public.event_locations WHERE event_id = p_event_id;
        v_location_ids := ARRAY[]::UUID[];
        FOR v_loc IN
            SELECT loc FROM jsonb_array_elements(p_locations) WITH ORDINALITY AS t(loc, ord) ORDER BY ord
        LOOP
            INSERT INTO public.event_locations (
                event_id, name, latitude, longitude, is_primary, order_index
            ) VALUES (
                p_event_id,
                v_loc->>'name',
                (v_loc->>'latitude')::DOUBLE PRECISION,
                (v_loc->>'longitude')::DOUBLE PRECISION,
                (v_loc->>'is_primary')::BOOLEAN,
                (v_loc->>'order_index')::INTEGER
            )
            RETURNING id INTO v_inserted_id;
            v_location_ids := array_append(v_location_ids, v_inserted_id);
        END LOOP;
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

    -- Replace segments. NULL = leave existing segments untouched. An empty
    -- array means "delete all segments". Any non-empty value triggers a
    -- full replacement.
    IF p_segments IS NOT NULL THEN
        DELETE FROM public.event_segments WHERE event_id = p_event_id;

        IF jsonb_array_length(p_segments) > 0 THEN
            -- If locations were not replaced in this call, populate
            -- v_location_ids from existing rows ordered (created_at,
            -- order_index, id). app/repositories/event.py::get_event_locations
            -- uses the same ORDER BY, so the client's `location_index`
            -- references the same positional list it just read.
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
                    p_event_id,
                    v_segment_location_id,
                    (v_seg->>'order_index')::INT,
                    (v_seg->>'start_datetime')::TIMESTAMPTZ,
                    (v_seg->>'end_datetime')::TIMESTAMPTZ,
                    v_seg->>'description'
                );
            END LOOP;
        END IF;
    END IF;

    -- Return updated event
    SELECT to_jsonb(e) INTO v_result
    FROM public.events e
    WHERE e.id = p_event_id;

    RETURN v_result;
END;
$$;
