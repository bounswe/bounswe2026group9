# Issue #278 Roadmap — Event Recommendation Notifications (Backend)

Sub-issue of #275. Implement an `event_recommended` notification type that fires when a host publishes a new event, targeting users whose past attendance pattern (categories) matches.

---

## Goal in one sentence

When `change_event_status(draft → published)` runs, find users who have a `going` attendance on an `ended` event in any of the new event's categories, then bulk-insert `event_recommended` notifications for them — respecting privacy, host-self exclusion, and a per-user daily cap.

---

## Step 1 — DB migration: extend notification types

**File:** `backend/sql/012_add_event_recommended_notification.sql` (new)

```sql
ALTER TABLE public.notifications
  DROP CONSTRAINT IF EXISTS notifications_type_check;

ALTER TABLE public.notifications
  ADD  CONSTRAINT notifications_type_check
       CHECK (type IN (
         'event_updated',
         'event_cancelled',
         'event_deleted',
         'access_request',
         'access_approved',
         'access_rejected',
         'event_recommended'
       ));
```

> Audit the current CHECK list against `002_create_core_tables.sql:298-312` and the access-request migration so we don't drop existing types.

Run on Supabase before deploy.

---

## Step 2 — Repository: candidate user query

**File:** `backend/app/repositories/notification.py`

Add:

```python
def count_recommendations_since(
    db: Client, user_id: str, cutoff_iso: str
) -> int:
    """How many event_recommended notifications were sent to user since cutoff."""
```

**File:** `backend/app/repositories/attendance.py`

Add:

```python
def find_recommendation_candidates(
    db: Client,
    category_ids: list[str],
    days: int = 90,
) -> set[str]:
    """
    Users with status='going' on an event whose status='ended',
    whose end_datetime is within the last `days` days,
    and whose categories overlap any of `category_ids`.
    """
```

Two-step query (Supabase REST has no joins across multiple tables on one call):
1. `event_categories.select(event_id).in_(category_id, category_ids)` → set of event_ids in those categories
2. `events.select(id).in_(id, event_ids).eq(status, 'ended').gte(end_datetime, cutoff)` → filter to ended-recent
3. `attendances.select(user_id).in_(event_id, ended_event_ids).eq(status, 'going')` → unique user_ids

Return `set[str]`.

---

## Step 3 — Service: recommendation emitter

**File:** `backend/app/services/recommendation_emitter.py` (new)

```python
MAX_RECOMMENDATIONS_PER_DAY = 3
ATTENDANCE_LOOKBACK_DAYS = 90

def emit_event_recommendations(db, event_id: str, host_id: str) -> int:
    """
    Called after change_event_status promotes an event to published.
    Returns the number of notifications inserted.
    """
```

Flow:
1. Load the event. **Skip if `visibility == 'private'`** (no recommendations for private events).
2. Load the event's category_ids.
3. `attendance_repo.find_recommendation_candidates(category_ids, days=90)` → candidate_ids.
4. Drop the host: `candidate_ids.discard(host_id)`.
5. Drop users who already have an `attendances` or `bookmarks` row for this event (avoid duplicate signals — they'll get the regular update channel).
6. **Drop users who hit the daily cap:** for each candidate, `notification_repo.count_recommendations_since(user_id, now - 24h)`. Skip if `>= 3`.
7. Pick a category-name string for the message: take the first category name, e.g. `"Based on events you attended in Jazz"`.
8. Build dict rows: `{user_id, event_id, type: "event_recommended", message, is_read: False}`.
9. `notification_repo.insert_notifications_bulk(rows)`.

Step 6 looks N+1 but with `MAX_RECOMMENDATIONS_PER_DAY = 3` and a small candidate pool it's fine for MVP-scale. Can be optimized later.

---

## Step 4 — Hook into publish path

**File:** `backend/app/services/event.py` — `change_event_status()`, draft→published branch (around line 711, after `update_event_status`).

```python
event_repo.update_event_status(db, event_id, new_status)

# NEW
if current == "draft" and new_status == "published":
    try:
        from app.services.recommendation_emitter import emit_event_recommendations
        emit_event_recommendations(db, event_id, user_id)
    except Exception as exc:
        # Recommendations are best-effort — never fail the publish on emitter error
        logger.warning("recommendation emitter failed: %s", exc)

if new_status == "cancelled":
    ...
```

Wrap in `try/except` so a recommendation failure never blocks the publish itself.

---

## Step 5 — Tests

**File:** `backend/tests/test_recommendation_emitter.py` (new)

Cover:

| # | Scenario | Expectation |
|---|---|---|
| 1 | User attended ended jazz event → host publishes new jazz event | User receives 1 `event_recommended` notification |
| 2 | User has no attendance history | No notification |
| 3 | Host publishes event → host themselves never gets it | host_id excluded |
| 4 | New event is `private` | No notifications emitted at all |
| 5 | Candidate already bookmarked the new event | Skipped (no double signal) |
| 6 | User already has 3 recommendations today → publish a 4th match | Capped at 3 (no new row) |
| 7 | Categories don't overlap | No notification |
| 8 | Attendance is on a future/published event (not yet ended) | Not counted as a match |
| 9 | Bulk: 50 candidates, all valid | Single bulk insert; 50 rows persisted |

Reuse fixtures from `test_notification_emitter.py` (`_create_test_user`, `_create_published_event`, `_add_attendance`).

Also extend `tests/test_events.py::TestChangeEventStatus::test_draft_to_published_with_image` (or add a sibling test) to assert that publishing also fires the recommendation emitter.

---

## Step 6 — Frequency-cap config (optional, MVP-friendly default)

For now hardcode `MAX_RECOMMENDATIONS_PER_DAY = 3` as a module constant. If we later want to tune it without redeploy, mirror the `rate_limit_config` table pattern (`backend/sql/002:341-357`) and add a `notification_frequency_config` table. Don't ship that table for this issue — keep scope tight.

---

## Out of scope for this issue

- Web UI rendering for `event_recommended` (separate task in #275)
- Mobile UI rendering (separate task in #275)
- Smarter matching beyond category overlap (host-affinity, geo proximity, ML scoring) — leave a TODO comment; scope explicitly says "start simple"

---

## Files I will touch

| File | Change |
|---|---|
| `backend/sql/012_add_event_recommended_notification.sql` | NEW migration extending CHECK |
| `backend/app/repositories/attendance.py` | NEW `find_recommendation_candidates()` |
| `backend/app/repositories/notification.py` | NEW `count_recommendations_since()` |
| `backend/app/services/recommendation_emitter.py` | NEW emitter module |
| `backend/app/services/event.py` | Inject emitter call into draft→published branch |
| `backend/tests/test_recommendation_emitter.py` | NEW test suite |
| `backend/tests/test_events.py` | Extend publish test |

Estimated diff: ~400-500 lines including tests.
