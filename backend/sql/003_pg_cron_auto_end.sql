-- Enable pg_cron extension (Supabase has it available)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Remove existing job if present (idempotent re-run)
SELECT cron.unschedule('auto-end-events')
WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'auto-end-events'
);

-- Schedule auto-end job: every 5 minutes, mark past events as ended
SELECT cron.schedule(
  'auto-end-events',
  '*/5 * * * *',
  $$UPDATE public.events
    SET status = 'ended'
    WHERE status IN ('published', 'updated')
    AND end_datetime < NOW()$$
);

-- Remove existing cleanup job if present (idempotent re-run)
SELECT cron.unschedule('cleanup-expired-tokens')
WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'cleanup-expired-tokens'
);

-- Schedule token cleanup: every hour, remove expired/revoked refresh tokens and expired verification tokens
SELECT cron.schedule(
  'cleanup-expired-tokens',
  '0 * * * *',
  $$DELETE FROM public.refresh_tokens WHERE revoked = true OR expires_at < NOW();
    DELETE FROM public.email_verification_tokens WHERE expires_at < NOW()$$
);
