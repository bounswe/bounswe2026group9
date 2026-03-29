-- Add phone_visibility column to users table
-- Controls whether phone_number is exposed in public host profiles
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS phone_visibility BOOLEAN DEFAULT FALSE;
