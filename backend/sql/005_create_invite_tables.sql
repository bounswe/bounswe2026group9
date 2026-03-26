-- ================================================================
-- 005_create_invite_tables.sql
-- Private event invite links and access request system
-- Depends on: 001_create_tables.sql (users), 002_create_core_tables.sql (events)
-- ================================================================

-- Invite links: host generates a token-based link to share
CREATE TABLE IF NOT EXISTS public.event_invites (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID        NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    created_by  UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token       TEXT        NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ,
    max_uses    INT         CHECK (max_uses IS NULL OR max_uses > 0),
    use_count   INT         NOT NULL DEFAULT 0 CHECK (use_count >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_invites_event_id ON public.event_invites (event_id);
CREATE INDEX IF NOT EXISTS idx_event_invites_token ON public.event_invites (token);

-- Access grants: tracks which users have been granted access to private events
CREATE TABLE IF NOT EXISTS public.event_access_grants (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID        NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    granted_via TEXT        NOT NULL CHECK (granted_via IN ('invite', 'request')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_event_access_grants_event_id ON public.event_access_grants (event_id);
CREATE INDEX IF NOT EXISTS idx_event_access_grants_user_id ON public.event_access_grants (user_id);

-- Access requests: users request access, host approves/denies
CREATE TABLE IF NOT EXISTS public.event_access_requests (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID        NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status      TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE (event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_event_access_requests_event_id ON public.event_access_requests (event_id);
CREATE INDEX IF NOT EXISTS idx_event_access_requests_status ON public.event_access_requests (event_id, status);

-- Grant access to service_role only
GRANT ALL ON public.event_invites TO service_role;
GRANT ALL ON public.event_access_grants TO service_role;
GRANT ALL ON public.event_access_requests TO service_role;
