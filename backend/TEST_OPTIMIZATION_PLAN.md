# Backend Test Optimization Plan

## Objective

Reduce backend CI runtime from the current ~25 minutes toward a more practical target of ~4-6 minutes, while keeping the test suite reliable and preserving isolation.

This plan is intentionally conservative:

- Do not trade speed for flaky CI.
- Do not weaken test isolation in ways that let parallel jobs or retries corrupt each other.
- Keep a small but strong integration layer against the real Supabase-backed system.
- Move only the right tests out of integration, not coverage itself.

## Constraints

The current backend suite is expensive because most tests are true integration tests:

- They hit the FastAPI app through HTTP.
- They read and write to remote Supabase.
- They create and clean up users, events, comments, invites, notifications, images, and tokens.
- They often repeat setup/teardown patterns per test.

Because of that, pure CI tuning alone will not get the suite from ~25 minutes to ~4 minutes. The big gains must come from changing the test pyramid:

- fewer remote integration tests
- more fast service/unit tests
- better CI layering

## Current State

### Current expensive areas

- `tests/test_events.py`
- `tests/test_discovery.py`
- `tests/test_invites.py`
- `tests/test_comments.py`
- `tests/test_notification_emitter.py`
- `tests/test_notifications.py`

### Current structural issues

- Most backend PRs currently trigger the full backend test suite.
- Many tests recreate similar users/events repeatedly.
- Cleanup work is repeated frequently and is remote-DB-bound.
- Some tests that only verify business logic still run as full integration tests.

## Optimization Principles

### 1. Keep isolation first

All optimizations must preserve:

- unique per-run identity generation
- deterministic cleanup boundaries
- no shard-to-shard cross-test pollution

### 2. Convert, do not delete blindly

We should not remove valuable coverage. Instead:

- move pure logic checks to unit/service tests
- keep one or two representative integration tests per endpoint family
- trim redundant integration variants only after equivalent lower-level coverage exists

### 3. Optimize in phases

Each phase should be independently safe and measurable.

## Phase 1: Safe CI Restructuring

### Goal

Get faster feedback without changing backend behavior.

### Actions

- Split fast auth-only unit tests from Supabase-backed integration tests.
- Keep lint in a separate job.
- Run the remaining integration tests separately from the fast unit tests.
- Reduce cleanup overhead without weakening run-level isolation.

### Expected impact

- Faster initial feedback on simple auth logic failures.
- Lower wall-clock time even before deeper refactors.
- Reduced cleanup query overhead.

### Status

This phase has already been prototyped locally.

## Phase 2: Integration Sharding

### Goal

Reduce wall-clock CI time by running independent integration groups in parallel.

### Recommended shard boundaries

- `auth-core`
  - `tests/test_auth.py`
  - `tests/test_auth_integration.py`
  - `tests/test_categories.py`
  - `tests/test_health.py`
  - `tests/test_users.py`

- `events`
  - `tests/test_events.py`

- `discovery`
  - `tests/test_discovery.py`

- `comments-invites`
  - `tests/test_comments.py`
  - `tests/test_invites.py`

- `media-notifications`
  - `tests/test_images.py`
  - `tests/test_bookmarks.py`
  - `tests/test_attendances.py`
  - `tests/test_notifications.py`
  - `tests/test_notification_emitter.py`

### Isolation rule

Every shard must use a distinct `TEST_RUN_ID` suffix so that per-shard cleanup never touches another shard's data.

### Observability

Add duration reporting to integration jobs:

- `--durations=15`
- `--durations-min=1.0`

This lets us tune shards using real timing data rather than guesses.

### Status

This phase has already been prototyped locally.

## Progress Snapshot

The following parts of the plan have already been implemented locally:

- fast auth-only unit tests split into dedicated `*_unit.py` files
- separate CI jobs for `lint`, `unit-fast`, and sharded integration runs
- shard-specific `TEST_RUN_ID` suffixing to preserve cleanup isolation
- cheaper per-test cleanup using a single email-pattern delete tied to `TEST_RUN_ID`
- duration reporting for integration shards
- first wave of unit extraction for:
  - notification emitter business rules
  - event datetime validation
  - event auto-end helper logic
- first wave of integration trimming for:
  - redundant notification-emitter recipient variants
  - redundant event datetime validation variants

Still intentionally deferred because they are higher-risk:

- aggressive fixture scope widening for mutable DB-backed setup
- backend-internal change detection
- `xdist` or parallel execution inside a shard
- moving large discovery/invites/comments coverage blocks without real CI timing data

## Phase 3: Convert Pure Business Logic Tests Out of Integration

### Goal

Shrink the remote-Supabase portion of the suite by moving pure logic into unit/service tests.

### High-value candidates

#### Auth

Already started:

- password hashing
- JWT encode/decode
- token expiry behavior

These belong in a pure unit layer and should stay there.

#### Event validation logic

Candidates to move from integration to unit/service tests:

- `validate_event_datetime()` in `app/services/event.py`
- validation around past/future datetime ordering
- other pure helper-level validations that do not require DB state

Current integration candidates in `tests/test_events.py`:

- invalid datetime
- past start validation

These are currently paying full HTTP + DB cost to test logic that lives in pure service helpers.

#### Notification emitter

`app/services/notification_emitter.py` is an especially strong unit-test candidate.

Current tests in `tests/test_notification_emitter.py` perform full user/event setup and DB mutation to validate:

- affected user selection
- host exclusion
- duplicate recipient prevention
- no-op behavior when there are no recipients

A faster test layer should instead mock repository/DB reads and assert:

- going users are included
- interested users are included
- bookmark users are included
- host is excluded
- duplicates collapse to one notification
- zero recipients returns `0`

Keep only one integration smoke test to ensure the emitter still works against the real persistence layer.

#### Comment, bookmark, attendance, invite service rules

Many negative-path rules can be unit-tested at the service level with mocked repository results:

- event not found
- invalid event status
- host cannot attend own event
- permission checks
- duplicate bookmark handling
- wrong comment ownership

These do not all need to remain full HTTP + Supabase tests.

### Expected impact

This phase is the main step that moves the suite from "faster" to "actually fast."

### Status

This phase is now partially prototyped locally.

## Phase 4: Reduce Redundant Integration Coverage

### Goal

Keep integration coverage strong, but stop paying remote DB cost for repeated variations that test the same path.

### Strategy

For each endpoint family, keep:

- 1-2 happy-path integration tests
- 1-2 key authorization tests
- 1-2 key persistence/side-effect tests

Then remove or downgrade redundant variants once lower-level coverage exists.

### File-by-file guidance

#### `tests/test_discovery.py`

This file has a combinatorial explosion of search/filter/pagination cases.

Keep in integration:

- basic public listing
- one search test
- one category filter test
- one temporal filter test
- one pagination test
- one combined-filters test

Candidates to reduce after lower-level coverage exists:

- multiple near-duplicate empty-result variants
- repeated sorting/pagination edge combinations
- overlapping filter combinations that exercise the same SQL path

#### `tests/test_events.py`

Keep in integration:

- create draft event
- publish flow
- get event full vs limited
- update event as host
- invalid host/non-host permission checks
- status transitions

### Status

The first conservative reduction pass is now prototyped locally for:

- notification-emitter recipient variants
- event datetime validation variants

Move or reduce:

- pure validation checks
- request-shape failures already covered by Pydantic/FastAPI validation

#### `tests/test_comments.py`

Keep in integration:

- create comment on published event
- list comments with user data
- delete by owner
- delete by host

Move/reduce:

- repeated invalid status permutations after service tests are added

#### `tests/test_invites.py`

Keep in integration:

- private event invite creation
- accept invite
- access request approve/deny

Move/reduce:

- repeated permission failures if covered at service level

#### `tests/test_notifications.py`

Keep in integration:

- list own notifications
- mark one as read
- mark all as read

Move/reduce:

- repetitive pagination/order variants if notification list shaping is separately validated

## Phase 5: Shared Setup Refactor

### Goal

Reduce repeated boilerplate and repeated remote setup patterns without weakening test isolation.

### Safe shared-fixture targets

- `db` fixture as session-scoped client object
- email-sending patch as session-scoped autouse fixture
- central helper for creating a fully published event with image
- central helper for creating a registered and/or logged-in user

### Important caution

Do **not** make mutable user/event data session-scoped if tests modify them.

Good candidates:

- read-only helpers
- reusable factory helpers

Risky candidates:

- shared mutable events
- shared mutable users reused across tests

## Phase 6: Add a Slow/Optional Workflow

### Goal

Move the slowest or broadest end-to-end behaviors out of the default PR path if needed.

### Possible structure

- PR CI:
  - lint
  - fast unit
  - integration shards

- optional/manual workflow:
  - very broad end-to-end flows
  - extra notification scenarios
  - cross-feature regression sweeps

This follows the same spirit as `Ai-Chief-of-Staff`, where not every expensive test has to run in the main PR loop.

## Recommended Sequence

### Already prototyped locally

1. Safe CI split
2. Integration shard split
3. Cheaper cleanup pattern

### Next recommended implementation order

4. Add service/unit tests for `notification_emitter`
5. Add service/unit tests for pure event validation helpers
6. Move selected negative-path comment/bookmark/attendance rules to service tests
7. Trim redundant integration variants only after lower-level coverage lands
8. Re-evaluate CI timings and rebalance shards
9. Optionally introduce a separate slow workflow

## Expected Runtime Progression

These are realistic estimates, not guarantees.

### Before optimization

- ~25 minutes

### After CI split + shard split + cleanup improvement

- likely ~8-12 minutes

### After unit extraction and integration slimming

- likely ~4-6 minutes

### Best case

- ~3-5 minutes

That best-case outcome requires real reduction in remote integration volume, not only CI restructuring.

## What We Should Avoid

- running xdist against the same remote Supabase without very careful isolation rules
- replacing strong integration coverage with weak mocks
- session-scoping mutable fixtures that can leak state across tests
- adding clever backend-internal change detection that risks skipping the wrong shard

## Success Criteria

- PR feedback becomes meaningfully faster
- flaky failures do not increase
- each shard only cleans up its own data
- integration coverage remains meaningful
- total wall-clock CI time trends toward the 4-6 minute range

## Notes

The main bottleneck is not Python itself alone; it is the combination of:

- Python app startup
- HTTP-level integration testing
- remote Supabase latency
- repeated per-test setup/cleanup

The winning strategy is therefore:

- make the integration layer smaller but stronger
- move pure logic downward into unit/service tests
- keep the remaining remote integration layer focused and intentional
