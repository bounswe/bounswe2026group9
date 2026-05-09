-- ================================================================
-- 018_add_checkin_to_attendances.sql
-- QR check-in support for the attendances table.
-- Depends on: 002_create_core_tables.sql (attendances)
-- ================================================================

-- Signed token issued when the user goes to an event.
-- Stored so the check-in endpoint can look up by token quickly.
ALTER TABLE public.attendances
    ADD COLUMN IF NOT EXISTS check_in_token TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS checked_in_at  TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_attendances_check_in_token
    ON public.attendances (check_in_token)
    WHERE check_in_token IS NOT NULL;
