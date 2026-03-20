-- ================================================================
-- 002_create_core_tables.sql
-- Core data model tables for Social Event Mapper
-- Depends on: 001_create_tables.sql (public.users must exist)
-- ================================================================


-- ================================================================
-- EXTEND USERS TABLE
-- Add default map area preference (user-selected, not GPS)
-- ================================================================

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS default_location_lat  DECIMAL(9, 6),
    ADD COLUMN IF NOT EXISTS default_location_lng  DECIMAL(9, 6),
    ADD COLUMN IF NOT EXISTS default_location_name VARCHAR(200);


-- ================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- Reusable trigger to auto-update updated_at on row changes
-- ================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ================================================================
-- CATEGORIES
-- ================================================================

CREATE TABLE IF NOT EXISTS public.categories (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,
    is_predefined BOOLEAN      NOT NULL DEFAULT FALSE,
    is_approved   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT categories_name_unique UNIQUE (name)
);

-- Predefined categories are auto-approved
INSERT INTO public.categories (name, is_predefined, is_approved) VALUES
    ('Music',             TRUE, TRUE),
    ('Sports',            TRUE, TRUE),
    ('Arts & Culture',    TRUE, TRUE),
    ('Food & Drink',      TRUE, TRUE),
    ('Technology',        TRUE, TRUE),
    ('Education',         TRUE, TRUE),
    ('Health & Wellness', TRUE, TRUE),
    ('Outdoor',           TRUE, TRUE),
    ('Community',         TRUE, TRUE),
    ('Nightlife',         TRUE, TRUE),
    ('Business',          TRUE, TRUE),
    ('Family',            TRUE, TRUE),
    ('Gaming',            TRUE, TRUE),
    ('Film & Media',      TRUE, TRUE),
    ('Travel',            TRUE, TRUE)
ON CONFLICT (name) DO NOTHING;


-- ================================================================
-- EVENTS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.events (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id           UUID         NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title             VARCHAR(200) NOT NULL,
    description       TEXT         NOT NULL,
    start_datetime    TIMESTAMPTZ  NOT NULL,
    end_datetime      TIMESTAMPTZ  NOT NULL,
    visibility        TEXT         NOT NULL DEFAULT 'public'
                                   CHECK (visibility IN ('public', 'private')),
    is_age_restricted BOOLEAN      NOT NULL DEFAULT FALSE,
    attendee_limit    INT          CHECK (attendee_limit IS NULL OR attendee_limit > 0),
    attendee_count    INT          NOT NULL DEFAULT 0 CHECK (attendee_count >= 0),
    status            TEXT         NOT NULL DEFAULT 'draft'
                                   CHECK (status IN ('draft', 'published', 'updated', 'cancelled', 'ended')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT end_after_start CHECK (end_datetime > start_datetime),
    CONSTRAINT attendee_count_within_limit CHECK (
        attendee_limit IS NULL OR attendee_count <= attendee_limit
    )
);

CREATE INDEX IF NOT EXISTS idx_events_host_id        ON public.events (host_id);
CREATE INDEX IF NOT EXISTS idx_events_status         ON public.events (status);
CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON public.events (start_datetime);
CREATE INDEX IF NOT EXISTS idx_events_end_datetime   ON public.events (end_datetime);
CREATE INDEX IF NOT EXISTS idx_events_visibility     ON public.events (visibility);

-- Partial index for discovery queries (published + updated events only)
CREATE INDEX IF NOT EXISTS idx_events_discoverable
    ON public.events (start_datetime, end_datetime)
    WHERE status IN ('published', 'updated');

CREATE TRIGGER events_set_updated_at
    BEFORE UPDATE ON public.events
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ================================================================
-- EVENT LOCATIONS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.event_locations (
    id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID          NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    name        VARCHAR(200)  NOT NULL,
    latitude    DECIMAL(9, 6) NOT NULL,
    longitude   DECIMAL(9, 6) NOT NULL,
    is_primary  BOOLEAN       NOT NULL DEFAULT FALSE,
    order_index INT           NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT latitude_range  CHECK (latitude  BETWEEN -90  AND  90),
    CONSTRAINT longitude_range CHECK (longitude BETWEEN -180 AND 180)
);

-- Enforce exactly one primary location per event
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_locations_one_primary
    ON public.event_locations (event_id)
    WHERE is_primary = TRUE;

CREATE INDEX IF NOT EXISTS idx_event_locations_event_id ON public.event_locations (event_id);


-- ================================================================
-- EVENT IMAGES
-- ================================================================

CREATE TABLE IF NOT EXISTS public.event_images (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID        NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    image_url   TEXT        NOT NULL,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_images_event_id ON public.event_images (event_id);


-- ================================================================
-- EVENT CATEGORIES  (junction table — many-to-many)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.event_categories (
    event_id    UUID NOT NULL REFERENCES public.events(id)     ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES public.categories(id) ON DELETE RESTRICT,
    PRIMARY KEY (event_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_event_categories_category_id ON public.event_categories (category_id);


-- ================================================================
-- VENUE METADATA  (optional 1:1 with event)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.venue_metadata (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id            UUID        NOT NULL UNIQUE REFERENCES public.events(id) ON DELETE CASCADE,
    price               VARCHAR(50),            -- e.g. 'free', 'paid', '€10'
    language            VARCHAR(50),
    health_requirements TEXT,
    wheelchair_access   BOOLEAN     NOT NULL DEFAULT FALSE,
    accessible_restroom BOOLEAN     NOT NULL DEFAULT FALSE,
    elevator_available  BOOLEAN     NOT NULL DEFAULT FALSE,
    seating_available   BOOLEAN     NOT NULL DEFAULT FALSE,
    captions_support    BOOLEAN     NOT NULL DEFAULT FALSE,
    quiet_friendly      BOOLEAN     NOT NULL DEFAULT FALSE
);


-- ================================================================
-- EQUIPMENT REQUIREMENTS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.equipment_requirements (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID         NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    item_name   VARCHAR(200) NOT NULL,
    is_required BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_equipment_event_id ON public.equipment_requirements (event_id);


-- ================================================================
-- BOOKMARKS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.bookmarks (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES public.users(id)   ON DELETE CASCADE,
    event_id   UUID        NOT NULL REFERENCES public.events(id)  ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_event_id ON public.bookmarks (event_id);


-- ================================================================
-- ATTENDANCES
-- status: 'going' counts toward capacity, 'interested' does not
-- ================================================================

CREATE TABLE IF NOT EXISTS public.attendances (
    id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID        NOT NULL REFERENCES public.users(id)   ON DELETE CASCADE,
    event_id  UUID        NOT NULL REFERENCES public.events(id)  ON DELETE CASCADE,
    status    TEXT        NOT NULL CHECK (status IN ('going', 'interested', 'cancelled')),
    marked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_attendances_event_id ON public.attendances (event_id);
CREATE INDEX IF NOT EXISTS idx_attendances_status   ON public.attendances (event_id, status);

-- Trigger: keep events.attendee_count in sync with 'going' attendances
CREATE OR REPLACE FUNCTION public.sync_attendee_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status = 'going' THEN
            UPDATE public.events SET attendee_count = attendee_count + 1
            WHERE id = NEW.event_id;
        END IF;

    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != 'going' AND NEW.status = 'going' THEN
            UPDATE public.events SET attendee_count = attendee_count + 1
            WHERE id = NEW.event_id;
        ELSIF OLD.status = 'going' AND NEW.status != 'going' THEN
            UPDATE public.events SET attendee_count = attendee_count - 1
            WHERE id = NEW.event_id;
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.status = 'going' THEN
            UPDATE public.events SET attendee_count = attendee_count - 1
            WHERE id = OLD.event_id;
        END IF;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER attendances_sync_count
    AFTER INSERT OR UPDATE OR DELETE ON public.attendances
    FOR EACH ROW EXECUTE FUNCTION public.sync_attendee_count();


-- ================================================================
-- COMMENTS
-- ================================================================

CREATE TABLE IF NOT EXISTS public.comments (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES public.users(id)   ON DELETE CASCADE,
    event_id   UUID        NOT NULL REFERENCES public.events(id)  ON DELETE CASCADE,
    text       TEXT        NOT NULL CHECK (char_length(text) >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_event_id ON public.comments (event_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id  ON public.comments (user_id);


-- ================================================================
-- RATINGS  (registered user rates a host)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.ratings (
    id         UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    rater_id   UUID          NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    host_id    UUID          NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    score      DECIMAL(3, 2) NOT NULL CHECK (score >= 1.00 AND score <= 5.00),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (rater_id, host_id),
    CONSTRAINT no_self_rating CHECK (rater_id <> host_id)
);

CREATE INDEX IF NOT EXISTS idx_ratings_host_id ON public.ratings (host_id);


-- ================================================================
-- NOTIFICATIONS
-- event_id kept nullable: event may be deleted after notification is sent
-- ================================================================

CREATE TABLE IF NOT EXISTS public.notifications (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES public.users(id)  ON DELETE CASCADE,
    event_id   UUID        REFERENCES public.events(id)          ON DELETE SET NULL,
    type       TEXT        NOT NULL
                           CHECK (type IN ('event_updated', 'event_cancelled', 'event_deleted')),
    message    TEXT        NOT NULL,
    is_read    BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id      ON public.notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread  ON public.notifications (user_id, is_read)
    WHERE is_read = FALSE;


-- ================================================================
-- REPORTS
-- target_type 'event'        -> target_id references events.id
-- target_type 'host_profile' -> target_id references users.id
-- Polymorphic reference: no FK to keep schema flexible
-- ================================================================

CREATE TABLE IF NOT EXISTS public.reports (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    target_type TEXT        NOT NULL CHECK (target_type IN ('event', 'host_profile')),
    target_id   UUID        NOT NULL,
    reason      TEXT        NOT NULL CHECK (char_length(reason) >= 1),
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_status      ON public.reports (status);
CREATE INDEX IF NOT EXISTS idx_reports_target      ON public.reports (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON public.reports (reporter_id);


-- ================================================================
-- RATE LIMIT CONFIG  (admin-managed, single-row config table)
-- ================================================================

CREATE TABLE IF NOT EXISTS public.rate_limit_config (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    max_events_per_user INT         NOT NULL DEFAULT 10
                                    CHECK (max_events_per_user > 0),
    time_window_hours   INT         NOT NULL DEFAULT 24
                                    CHECK (time_window_hours > 0),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER rate_limit_config_set_updated_at
    BEFORE UPDATE ON public.rate_limit_config
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Default config row
INSERT INTO public.rate_limit_config (max_events_per_user, time_window_hours)
SELECT 10, 24
WHERE NOT EXISTS (SELECT 1 FROM public.rate_limit_config);


-- ================================================================
-- GRANTS
-- Allow Supabase roles to access all tables in this schema
-- ================================================================

GRANT ALL ON ALL TABLES    IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;
