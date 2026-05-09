# OWASP-Oriented Security Audit

Issue #152 deliverable: an OWASP top-10–oriented review of the backend
with each finding either remediated or explicitly documented as
out-of-scope. Last audited 2026-05-07 against branch
`feat/backend-nfr-hardening` (one commit ahead of `main`'s
`8da9daf`).

Ten categories below follow the OWASP Top 10 (2021). For each, we list
where the relevant surface lives in the code, what defends it today,
and any leftover risk.

---

## A01 — Broken Access Control

**Surface**
- `app/middleware/auth.py::get_current_user` (JWT bearer dependency).
- `app/middleware/auth.py::require_role(*roles)` factory (admin-only
  endpoints — currently unused since admin/moderation features were
  not shipped, see issues #150, #151 closed as not planned).
- Per-resource ownership checks inside service functions (e.g.
  `services/event.py::update_event` `event["host_id"] != user_id` →
  403; `services/comment.py::delete_comment` owner-or-host check).
- Visibility-scoped read paths: `services/event.py::get_event_detail`
  applies `private` + access-grant logic before returning full detail;
  guests get a `LimitedResponse`.

**Defenses verified**
- Unit tests (`tests/test_event_crud_unit.py`,
  `tests/test_comment_unit.py`, `tests/test_invite_unit.py`) cover
  403/404 branches per service.
- E2E scenario `tests/e2e/test_private_access_flow.py` exercises the
  full public→private→approved access chain end-to-end.
- Backend-enforced — no client-side gating: `tests/test_invites.py`
  verifies that a guest hitting a private event without a grant
  receives a `LimitedResponse`, never the full payload.

**Findings**: none. Remaining hardening (admin role checks for the
yet-to-be-built moderation surface) is feature-blocked, not
audit-blocked.

---

## A02 — Cryptographic Failures

**Surface**
- Password hashing in `app/services/auth.py::hash_password` /
  `verify_password` — `bcrypt` 4.2 with cost factor 12 (library
  default). Stored as the hashed string in `users.hashed_password`.
- JWT signing in `app/services/auth.py::create_access_token` /
  `decode_access_token` — HS256 via `python-jose`, secrets from
  `settings.JWT_SECRET` / `settings.JWT_REFRESH_SECRET`. Tokens carry
  `sub` (user id), `email`, `iat`, `exp`.
- Refresh tokens are opaque random strings (`secrets.token_urlsafe(32)`),
  not JWTs. Stored hashed in `refresh_tokens.token`. The cookie carries
  the raw token; lookup is by hash equality.
- Email-verification tokens — same opaque-random pattern, hashed in
  `email_verification_tokens`.

**Defenses verified**
- No plaintext credentials at rest. Both token tables store hashes;
  raw values appear once in the wire response (cookie or query
  string), then are forgotten by the server.
- HTTPS terminated at nginx (`deploy/nginx/ec2-https.conf`); HSTS
  emitted by the reverse proxy.

**Findings**
- Refresh-token rotation is implemented but not yet measured; the
  legacy lane has integration coverage in `tests/test_auth.py`.
- `JWT_SECRET` is required from env; the default `.env.example` ships
  with a placeholder that triggers `openssl rand -hex 32` per the
  README. No fallback secret in code.

---

## A03 — Injection

**Surface**
- Database access: every service goes through `supabase-py`'s query
  builder (`db.table(name).select(cols).eq(col, val)`) or one of the
  two atomic RPCs (`create_event_atomic`, `update_event_atomic`) in
  `app/repositories/event.py`. The query builder parameterises every
  filter; the RPCs receive JSONB inputs that are bound parameters,
  not interpolated strings.
- The `unaccent_search` helper in `sql/016_unaccent_search.sql`
  composes a `LIKE` pattern from a parameter; the parameter is bound
  via PL/pgSQL's `EXECUTE … USING` style (the function builds the
  `%norm%` pattern internally — no string concat across the trust
  boundary).
- `os.path` / shell calls — none. The image upload path uses
  `Pillow` for format detection + Supabase Storage for the upload;
  the URL split that strips the bucket prefix is over a known
  `f"/{BUCKET_NAME}/"` separator and never concatenated into a shell
  command.
- HTML rendering — the only HTML the backend produces is the
  verification email body in `app/services/email.py::send_verification_email`,
  rendered as a Python f-string. The interpolated value is the raw
  verification URL (frontend domain + opaque token); no user-supplied
  string lands here, so XSS via that path is not reachable.

**Defenses verified**
- Bandit (`bandit -c pyproject.toml -r app/`) clean as of this commit
  (0 findings) — see `.github/workflows/backend-ci.yml::static-analysis`.
- No `eval` / `exec` / `subprocess.run(shell=True)` calls in `app/`.

**Findings**: none.

---

## A04 — Insecure Design

**Surface / decisions**
- Rate limiting on auth endpoints: `slowapi` per-IP limits in
  `app/rate_limit.py` (5/min on register, 10/min on login, 3/min on
  resend-verification). Disabled in test (`TESTING=1`) so the suite
  doesn't trip itself.
- Account lockout: `users.failed_login_attempts` + `locked_until` —
  five failed logins → 15-minute lock. Clears on successful login.
  Covered by `tests/test_auth.py::TestLogin::test_account_lockout` (in
  the legacy lane).
- Event creation rate limit: DB-driven `rate_limit_config` table read
  per request in `services/event.py::check_rate_limit`. Service-role
  email `muhittin0koybasi@gmail.com` is exempted.
- Refresh-token rotation: every refresh issues a new token and revokes
  the old one (`tests/test_auth.py::test_refresh_old_token_revoked`).
- Self-rating prevented in service layer
  (`services/rating.py::rate_host`); duplicate-rating is upsert by
  `(rater_id, host_id)`.

**Findings**: none. The rate-limit bypass via the exempt email is
intentional (load-test/owner exemption), not a privilege escalation.

---

## A05 — Security Misconfiguration

**Surface**
- CORS in `app/main.py`: origins read from `CORS_ORIGINS`, not `*`.
  Allowed methods enumerated; `allow_credentials=True`.
- HSTS: emitted by nginx in production (`deploy/nginx/ec2-https.conf`),
  not by the app.
- Refresh cookie attributes (`app/routers/auth.py::_set_refresh_cookie`):
  `httponly=True`, `secure=settings.is_production`, `samesite="lax"`,
  `max_age=30 days`.
- Rate-limiter disabled by `TESTING=1` env var, set automatically by
  `tests/conftest.py`. Production never sets `TESTING=1`.
- Image upload limits: 10 images per event, 20 MB max per image,
  format whitelist `{JPEG, PNG, WebP}` — enforced in
  `services/image.py`.

**Findings**
- `secure=False` in dev is intentional (localhost over HTTP).
- The `samesite=lax` choice is correct for the cookie-based refresh
  flow with cross-origin SPAs; `strict` would block legitimate
  redirects from the OAuth provider.

---

## A06 — Vulnerable and Outdated Components

**Surface**: `backend/requirements.txt`. Pinned versions audited for
known CVEs as of audit date.

**Defenses verified**
- All deps version-pinned (no floating ranges).
- bandit + ruff in CI (`backend-ci.yml::static-analysis`).
- Dependency renewal cadence is manual today; suggest adding
  Dependabot in a follow-up.

**Findings**: none specific. Recommend Dependabot for automated CVE
alerts.

---

## A07 — Identification and Authentication Failures

**Surface**: see A02 + A04. JWT bearer for the API, opaque refresh
tokens stored hashed, account lockout, rate-limited register/login.

**Findings**: none.

---

## A08 — Software and Data Integrity Failures

**Surface**
- No CI/CD signing today; Docker images pushed to Docker Hub from a
  GitHub Actions workflow over an OIDC-equivalent token.
- No third-party JS pulled into the backend (HTML rendering is server-
  side only and self-contained for the verification email).
- Atomic event create/update goes through Postgres RPC functions
  defined in `sql/013_atomic_event_rpc_segments.sql` — single
  transaction, so partial-write data integrity issues can't leak.

**Findings**: none.

---

## A09 — Security Logging and Monitoring Failures

**Surface**
- Structured (JSON) logging installed in `app/logging_config.py`,
  configured at app import in `app/main.py`. Key actions
  (`event.create`, `event.update`, `event.publish`, `event.cancel`,
  `event.end`, `event.delete`) emit a structured INFO record with
  `event_id`, `user_id`, and action-specific context.
- Catch-all 5xx handler in `app/main.py` logs request method/path +
  exception class with `exc_info=True`. Operators can grep
  `action=http.unhandled_exception` to triage incidents.
- Storage cleanup failures during `delete_event` emit a structured
  WARNING; the DB delete still cascades.
- `tests/test_logging_unit.py` pins the field contract — adding a new
  action surface must keep the structured field shape compatible.

**Findings**: NFR-07 deliverable for this issue; closed.

---

## A10 — Server-Side Request Forgery

**Surface**
- Outbound HTTP calls: only Google's OAuth endpoints
  (`app/services/oauth.py`: token exchange + userinfo) and SMTP
  (`app/services/email.py`). All targets are static, configuration-
  controlled, never user-supplied.
- Image upload accepts a binary file, never a URL. No URL fetches
  inside the upload path.

**Findings**: none. SSRF surface is empty.

---

## NFR cross-references

| OWASP | NFR-issue mapping | Source |
|---|---|---|
| A01 | NFR-04 (private event backend-enforced) | E2E + unit |
| A02, A07 | — | unit-fast lane |
| A03 | — | bandit + manual review |
| A05 | NFR-03 (HTTPS) | nginx config |
| A09 | NFR-07 (structured logs) | `app/logging_config.py` |
| A10 | NFR-09 (no precise GPS persisted) | schema audit + Phase D test |

---

## Summary

No new findings to remediate. The audit confirms the surface is
defended at every category by either explicit code paths, test
coverage, or operational config (nginx). Outstanding hardening items
(Dependabot, refresh-token rotation hardening) are tracked as
follow-ups, not regressions.
