-- users tablosu
CREATE TABLE public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  hashed_password TEXT,
  phone_number TEXT,
  date_of_birth DATE,
  email_visibility BOOLEAN DEFAULT FALSE,
  role TEXT NOT NULL DEFAULT 'registered',
  auth_provider TEXT NOT NULL DEFAULT 'local',
  google_id TEXT UNIQUE,
  email_verified BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  failed_login_attempts INTEGER DEFAULT 0,
  locked_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON public.users (email);
CREATE INDEX idx_users_username ON public.users (username);

-- refresh_tokens tablosu
CREATE TABLE public.refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_token ON public.refresh_tokens (token);
CREATE INDEX idx_refresh_tokens_user_id ON public.refresh_tokens (user_id);

-- email_verification_tokens tablosu
CREATE TABLE public.email_verification_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_verification_tokens_token ON public.email_verification_tokens (token);
