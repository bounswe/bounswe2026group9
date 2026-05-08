# Backend Testing Guide

Four CI test lanes exist; pick one based on what you're verifying. The
fastest lane (unit) runs in under a second and never touches the
network — that's where most new tests should land. A fifth, hermetic
lane is local-only (no CI workflow drives it today).

## TL;DR — adding a test

| You're verifying… | Add it to | Why |
|-------------------|-----------|-----|
| A pure function or service branch with mockable dependencies | `tests/test_<service>_unit.py` | Sub-second, no docker, MagicMock against the repo Protocol |
| A response *shape* contract a frontend depends on | `tests/test_<area>_snapshot_unit.py` (syrupy) | Shape only; values normalised through `_normalise()` |
| A property over a generated input space | `tests/test_<area>_property_unit.py` (hypothesis) | Use the strategies in `tests/hypothesis_strategies.py` |
| A latency budget on a hot path | `tests/test_<area>_benchmarks_unit.py` (pytest-benchmark) | Snapshots committed; CI fails on >50% regression |
| One happy-path HTTP contract per endpoint | `tests/test_<router>.py` | Shared TEST_SUPABASE_* integration project |
| A multi-step user journey | `tests/e2e/test_<scenario>.py` | Same shared integration project; covers router → service → repo → DB |
| A SQL migration / RPC | `tests/db/test_migrate.py` (or sibling) | Local-only — Postgres testcontainer (PG_CONTAINER=1) |

## The five lanes

### 1. Unit-fast (`tests/test_*_unit.py`)
- 230+ tests, <1 s wall, zero network
- `SUPABASE_URL=fake` is enough; the conftest's `db` fixture is
  overridden inside each unit file to a `MagicMock`
- Drives each service through the keyword-default DI seam introduced
  in the repository-protocols pass:

  ```python
  event_service.create_event(
      db, user_id, body,
      events=mock_event_repo, users=mock_user_repo,
  )
  ```

- Run: `pytest tests/test_*_unit.py --no-cov`

### 2. Property (`tests/test_*_property_unit.py`)
- Hypothesis explores input spaces for the validators and
  normalisers
- Strategies live in `tests/hypothesis_strategies.py` and are reused
  by the unit suite
- Per-test fixture override: each property file declares a local
  `db` fixture so the autouse cleanup_test_users resolves to a
  MagicMock and never touches a real backend

### 3. Snapshot (`tests/test_*_snapshot_unit.py`)
- `syrupy` snapshots stored in `tests/__snapshots__/` and committed
  with the test
- Pin the *shape* — keys present, types, structure — not the values
  (UUIDs and timestamps are stripped by `_normalise()` before the
  diff)
- Regenerate after an intentional schema change:
  `pytest tests/test_*_snapshot_unit.py --snapshot-update`

### 4. Benchmark (`tests/test_ranking_benchmarks_unit.py`)
- `pytest-benchmark` times in-memory ranking on synthetic 5k-event
  datasets
- Snapshot-savable: `pytest tests/test_ranking_benchmarks_unit.py
  --benchmark-save=baseline`
- Compare against baseline:
  `pytest tests/test_ranking_benchmarks_unit.py --benchmark-compare=baseline`
- A regression of >50% should fail CI; the workflow doesn't gate
  yet, so reviewers eyeball the numbers in the run log

### 5. Hermetic integration (`PG_CONTAINER=1`, local-only)
- The same `tests/db/` migration + smoke suite plus the integration
  suite can run against a Postgres + PostgREST stack booted by
  testcontainers. No CI workflow drives it today — the previous
  ``backend-ci-hermetic.yml`` was removed because the container boot
  + auth-role wiring was unstable on hosted runners. Keep the local
  command around because the infrastructure code is still useful for
  one-off "is my migration self-consistent?" checks.
- Local:

  ```bash
  PG_CONTAINER=1 \
    JWT_SECRET=hermetic JWT_REFRESH_SECRET=hermetic \
    SUPABASE_URL=http://localhost:0 SUPABASE_KEY=bootstrap-only \
    pytest tests/ -v
  ```

- Per-test isolation is `TRUNCATE public.* RESTART IDENTITY CASCADE`
  — the autouse `cleanup_test_users` switches to TRUNCATE when
  `PG_CONTAINER=1`.

## Running the full local loop

```bash
# Fast feedback (unit + property + snapshot + benchmark smoke).
# All four families share the `_unit.py` suffix so the CI unit-fast
# glob picks them up automatically.
pytest tests/test_*_unit.py --no-cov --benchmark-disable

# Static analysis
ruff check .
mypy app | mypy-baseline filter
bandit -c pyproject.toml -r app/
```

The hermetic local lane needs Docker. The default CI lane runs against
the shared `TEST_SUPABASE_*` integration project — that's what gates
PRs today and that's what every `backend-ci.yml` job points at.

## Debugging a failing test

- Run a single shard: `pytest tests/test_discovery.py -v -ra`
- Re-run the last failures only: `pytest --lf`
- Dump the testcontainer DB after a failure:

  ```bash
  PG_CONTAINER=1 TC_KEEP=1 pytest tests/db -v
  # Inspect the live container with `docker ps`, attach with
  # `docker exec -it <id> psql -U postgres`
  ```

  (`TC_KEEP=1` is a convention; the conftest doesn't honour it
  today — to be added when somebody hits a real failure.)

## Conventions

- Unit tests: name `test_<service>_unit.py`, declare a local `db`
  MagicMock so the autouse fixture is satisfied without booting
  anything
- Repository tests: skip them — exercise the repo through a service
  unit test against its protocol
- Service tests with explicit fixture overrides should pass repos as
  keyword arguments (`events=...`) not via `monkeypatch`
- E2E tests: use `e2e_client` (not the top-level `client`) and
  `admin_db` (for setup that bypasses authz)
- Test names: `test_<subject>_<expected>` — verbose is fine,
  pytest's collection output is the read path
