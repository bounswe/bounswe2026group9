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
