# End-to-End Acceptance Tests (Playwright)

Implements the web acceptance test catalog defined in the
[Acceptance Testing Strategy](https://github.com/bounswe/bounswe2026group9/wiki/Acceptance%20Testing%20Strategy)
and the Lab 9 report.

## Test catalog

### Strategy regression set (Section 10)

| Spec | Wiki scenario |
|---|---|
| `auth-smoke.spec.ts` | Sanity / always runs (no seed) |
| `register-flow.spec.ts` | Register and login |
| `event-create.spec.ts` | Create and publish event |
| `tc-acc-evt-lifecycle-05.spec.ts` | Edit event + Cancel event |
| `discovery-browse.spec.ts` | Browse events in map / list view, open detail |
| `discovery-filters.spec.ts` | Apply discovery filters (quick, accessibility, past) |
| `tc-web-acc-06-suggested-filter.spec.ts` | Suggested discovery filter |
| `bookmark-event.spec.ts` | Bookmark event |
| `going-event.spec.ts` | Mark event as Going |
| `tc-acc-event-capacity-01.spec.ts` | Enforce capacity |
| `comment-event.spec.ts` | Comment on event |
| `rate-host.spec.ts` | Rate host |
| `host-profile.spec.ts` | View host profile |
| `notifications.spec.ts` | Receive update / cancellation notifications |
| `private-event-restriction.spec.ts` | Verify private event restriction |
| `recommendation-privacy.spec.ts` | Verify recommendation privacy |

### Lab 9 acceptance test owners

| Spec | Test ID | Owner |
|---|---|---|
| `tc-web-acc-06-suggested-filter.spec.ts` | TC-WEB-ACC-06 | Muhittin Köybaşı (AT06) |
| `tc-acc-event-capacity-01.spec.ts` | TC-ACC-EVENT-CAPACITY-01 | İbrahim Fırat Yoğurtçu (AT04) |
| `tc-acc-evt-lifecycle-05.spec.ts` | TC-ACC-EVT-LIFECYCLE-05 | Faik İhsan Südüpak (AT05) |

## Setup

```bash
cd frontend
npm install                       # picks up @playwright/test from package.json
npx playwright install chromium   # downloads the browser binary once
```

Make sure the backend is running on `http://localhost:8888` (or set
`API_BASE_URL`). Playwright will start `next dev` automatically; if you
already have it running on `:3000` it will reuse it.

## Running

```bash
npm run test:e2e           # headless, all specs
npm run test:e2e:ui        # interactive mode (great for debugging)
npm run test:e2e:report    # open the last HTML report
```

Target a single spec:

```bash
npx playwright test e2e/tc-web-acc-06-suggested-filter.spec.ts
```

## Required seed data

Specs that need backend state will **skip themselves** when the env
variables below are missing, so the suite is safe to run on a fresh
clone — only `auth-smoke.spec.ts`, `register-flow.spec.ts`, and the
guest paths of `discovery-browse.spec.ts` and `discovery-filters.spec.ts`
run without seed data.

| Env var | Used by | Purpose |
|---|---|---|
| `BASE_URL` | all | Frontend URL (default `http://localhost:3000`) |
| `API_BASE_URL` | capacity, private, event-create | Backend URL (default `http://localhost:8888`) |
| `E2E_USER_EMAIL` / `E2E_USER_PASSWORD` | bookmark, going, comment, rate-host, notifications, suggested, recommendation-privacy, private | Registered user, ideally with attendance history |
| `E2E_NEW_USER_PASSWORD` | register-flow | Password used for the randomly-generated email (default `Sm0kePass!23`) |
| `E2E_HOST_EMAIL` / `E2E_HOST_PASSWORD` | event-create, lifecycle | Host account that owns the lifecycle events |
| `E2E_USER_A_EMAIL` / `E2E_USER_A_PASSWORD` | capacity | Fills the last seat |
| `E2E_USER_B_EMAIL` / `E2E_USER_B_PASSWORD` | capacity | Blocked by FULL |
| `E2E_EVENT_FULL_ID` | capacity | Event with `attendeeLimit=2`, `going=1` at start |
| `E2E_EVENT_FUTURE_ID` | lifecycle | Future event owned by the host |
| `E2E_EVENT_ONGOING_ID` | lifecycle | Ongoing event owned by the host |
| `E2E_EVENT_PRIVATE_ID` | private-event-restriction | Private event the user does NOT host |
| `E2E_EVENT_GOING_ID` | going-event | Public, non-full, future event |
| `E2E_EVENT_COMMENT_ID` | comment-event | Event with comments open |
| `E2E_HOST_PROFILE_ID` | host-profile | Host with at least one event |
| `E2E_RATEABLE_HOST_ID` | rate-host | Host the test user is eligible to rate |
| `E2E_EXPECT_UPDATE_NOTIFICATION` | notifications | `1` if an update notification is seeded for the user |
| `E2E_EXPECT_CANCELLATION_NOTIFICATION` | notifications | `1` if a cancellation notification is seeded for the user |

Example `.env.e2e`:

```bash
BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8888

E2E_USER_EMAIL=user_42@example.com
E2E_USER_PASSWORD=Password123!

E2E_HOST_EMAIL=host@example.com
E2E_HOST_PASSWORD=Password123!

E2E_USER_A_EMAIL=user_a@example.com
E2E_USER_A_PASSWORD=User_A_Pass!23
E2E_USER_B_EMAIL=user_b@example.com
E2E_USER_B_PASSWORD=User_B_Pass!23

E2E_EVENT_FULL_ID=...
E2E_EVENT_FUTURE_ID=...
E2E_EVENT_ONGOING_ID=...
E2E_EVENT_PRIVATE_ID=...
E2E_EVENT_GOING_ID=...
E2E_EVENT_COMMENT_ID=...
E2E_HOST_PROFILE_ID=...
E2E_RATEABLE_HOST_ID=...
```

Load it with `set -a; source .env.e2e; set +a; npm run test:e2e`.

## Notes

- `playwright.config.ts` runs **one worker** because the specs mutate
  shared backend state (going-counts, cancellations, comments).
- Traces, screenshots, and video are kept on failure under
  `playwright-report/` and `test-results/` (both gitignored).
- If you do **not** want Playwright to spin up `next dev`, set
  `PLAYWRIGHT_NO_WEBSERVER=1` and run `npm run dev` yourself.
- Selectors lean on `getByRole`/`getByLabel`/text rather than CSS classes
  so they survive Tailwind refactors.
