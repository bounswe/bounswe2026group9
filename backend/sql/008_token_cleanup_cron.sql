-- 008: Schedule periodic cleanup of expired/revoked tokens
-- Run this in Supabase SQL Editor (requires pg_cron extension)

-- Clean up revoked or expired refresh tokens every 6 hours
SELECT cron.schedule(
    'cleanup-refresh-tokens',
    '0 */6 * * *',
    $$DELETE FROM public.refresh_tokens WHERE revoked = true OR expires_at < NOW()$$
);

-- Clean up expired email verification tokens every 6 hours
SELECT cron.schedule(
    'cleanup-verification-tokens',
    '0 */6 * * *',
    $$DELETE FROM public.email_verification_tokens WHERE expires_at < NOW()$$
);
