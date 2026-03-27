# Frontend

Next.js frontend for Social Event Mapper.

## Environment

Create a local env file from `.env.example` and point it at the backend:

```bash
cp .env.example .env.local
```

Default value:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8888
```

The frontend expects the backend refresh token to be stored in an HTTP-only
cookie, so authenticated requests always use `credentials: "include"`.

## Available scripts

```bash
npm run dev
npm run build
npm run lint
npm run typecheck
npm run check
```

## Auth flow in this branch

- `src/lib/api.ts` centralizes API access and retries authenticated requests
  after a successful `/auth/refresh`.
- `src/lib/session.ts` holds the client-side auth snapshot.
- `src/providers/auth-provider.tsx` exposes auth state globally through React
  context.
- `/login` handles local sign-in and Google sign-in entry.
- `/auth/callback` completes the Google callback flow by restoring the session.
- `/dashboard` is the protected route used to validate `/auth/me`, refresh
  rotation, and login redirection.

## Verification

1. Start the backend on `http://localhost:8888`.
2. Run `npm run dev`.
3. Open `http://localhost:3000/login`.
4. Sign in with a backend user and verify that:
   - `/dashboard` loads successfully
   - `Fetch /auth/me again` works
   - `Rotate session` succeeds
   - `Logout` clears the session and returns to login

Run `npm run check` before opening a PR.
