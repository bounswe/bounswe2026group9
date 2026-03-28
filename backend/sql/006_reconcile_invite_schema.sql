-- ================================================================
-- 006_reconcile_invite_schema.sql
-- Reconcile legacy invite schema drift in an existing Supabase project
-- Safe to run manually in Supabase SQL Editor
-- ================================================================

-- Canonical invite table is public.event_invites.
-- If the legacy table still exists:
-- - drop it when empty
-- - migrate rows when canonical is empty
-- - abort when both tables contain data
DO $$
DECLARE
    legacy_exists BOOLEAN;
    canonical_exists BOOLEAN;
    legacy_count BIGINT := 0;
    canonical_count BIGINT := 0;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'event_invitations'
    ) INTO legacy_exists;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'event_invites'
    ) INTO canonical_exists;

    IF legacy_exists THEN
        EXECUTE 'SELECT COUNT(*) FROM public.event_invitations' INTO legacy_count;
    END IF;

    IF canonical_exists THEN
        EXECUTE 'SELECT COUNT(*) FROM public.event_invites' INTO canonical_count;
    END IF;

    IF legacy_exists AND canonical_exists THEN
        IF legacy_count = 0 THEN
            EXECUTE 'DROP TABLE public.event_invitations';
        ELSIF canonical_count = 0 THEN
            EXECUTE $migrate$
                INSERT INTO public.event_invites (
                    id, event_id, created_by, token, expires_at, max_uses, use_count, created_at
                )
                SELECT
                    id, event_id, created_by, token, expires_at, max_uses, use_count, created_at
                FROM public.event_invitations
                ON CONFLICT (token) DO NOTHING
            $migrate$;
            EXECUTE 'DROP TABLE public.event_invitations';
        ELSE
            RAISE EXCEPTION
                'Both public.event_invitations and public.event_invites contain data. Reconcile rows manually before rerunning this script.';
        END IF;
    ELSIF legacy_exists AND NOT canonical_exists THEN
        EXECUTE 'ALTER TABLE public.event_invitations RENAME TO event_invites';
    END IF;
END $$;

DROP INDEX IF EXISTS public.idx_event_invitations_event_id;
DROP INDEX IF EXISTS public.idx_event_invitations_token;

CREATE INDEX IF NOT EXISTS idx_event_invites_event_id ON public.event_invites (event_id);
CREATE INDEX IF NOT EXISTS idx_event_invites_token ON public.event_invites (token);

-- Canonicalize access-request schema and status vocabulary.
ALTER TABLE public.event_access_requests
    ADD COLUMN IF NOT EXISTS message TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

UPDATE public.event_access_requests
SET
    status = CASE WHEN status = 'denied' THEN 'rejected' ELSE status END,
    updated_at = COALESCE(updated_at, NOW());

ALTER TABLE public.event_access_requests
    ALTER COLUMN updated_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE public.event_access_requests
    DROP CONSTRAINT IF EXISTS event_access_requests_status_check;

ALTER TABLE public.event_access_requests
    ADD CONSTRAINT event_access_requests_status_check
    CHECK (status IN ('pending', 'approved', 'rejected'));

DROP TRIGGER IF EXISTS event_access_requests_set_updated_at ON public.event_access_requests;

CREATE TRIGGER event_access_requests_set_updated_at
    BEFORE UPDATE ON public.event_access_requests
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP INDEX IF EXISTS public.idx_access_requests_event_id;
DROP INDEX IF EXISTS public.idx_access_requests_status;

CREATE INDEX IF NOT EXISTS idx_event_access_requests_event_id ON public.event_access_requests (event_id);
CREATE INDEX IF NOT EXISTS idx_event_access_requests_status ON public.event_access_requests (event_id, status);

-- Keep notification types aligned with access-request flow.
ALTER TABLE public.notifications
    DROP CONSTRAINT IF EXISTS notifications_type_check;

ALTER TABLE public.notifications
    ADD CONSTRAINT notifications_type_check
    CHECK (type IN (
        'event_updated',
        'event_cancelled',
        'event_deleted',
        'access_request',
        'access_approved',
        'access_rejected'
    ));
