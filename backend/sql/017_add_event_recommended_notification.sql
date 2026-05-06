-- Add 'event_recommended' to the notifications.type CHECK constraint.
--
-- Source for the existing types:
--   002_create_core_tables.sql defines event_updated / event_cancelled / event_deleted.
--   The access-request feature added event_request / access_approved / access_rejected
--   to the live DB through later DDL. This migration is the consolidated re-statement
--   of the constraint with the new type included.

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
        'access_rejected',
        'event_recommended'
    ));
