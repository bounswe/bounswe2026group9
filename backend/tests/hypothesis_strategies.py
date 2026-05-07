"""Reusable Hypothesis strategies for backend property tests.

The validators in `services.event` take rich, structured input — the
shape of valid + invalid values is small enough that a careful set of
strategies covers more ground than the example-based unit suite ever
will. The strategies here generate timezone-aware datetimes, valid
segment lists, and accessibility filter combinations so each test can
focus on the *invariant* it asserts rather than wrestling fixtures.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import strategies as st

from app.models.event import SegmentRequest


def aware_datetime(*, days_min: int = 1, days_max: int = 365) -> st.SearchStrategy[datetime]:
    """A timezone-aware UTC datetime, comfortably in the future.

    `days_min=1` keeps every value past `datetime.now(UTC)` so tests
    that only care about the "must be in the future" invariant don't
    have to special-case noon-today.
    """
    return st.builds(
        lambda offset_min: datetime.now(UTC) + timedelta(minutes=offset_min),
        st.integers(min_value=days_min * 24 * 60, max_value=days_max * 24 * 60),
    )


def event_window(
    *,
    duration_min_minutes: int = 30,
    duration_max_minutes: int = 24 * 60,
) -> st.SearchStrategy[tuple[datetime, datetime]]:
    """A `(start, end)` pair where `end - start` lies in the allowed band.

    Many event-level invariants depend on a sane window — sampling a
    free pair of datetimes and rejecting bad ones wastes cycles, so
    we build the pair directly.
    """
    return st.builds(
        lambda start, mins: (start, start + timedelta(minutes=mins)),
        aware_datetime(),
        st.integers(min_value=duration_min_minutes, max_value=duration_max_minutes),
    )


def contiguous_segments(
    *,
    location_count: int,
    event_start: datetime,
    event_end: datetime,
    max_count: int = 6,
) -> st.SearchStrategy[list[SegmentRequest]]:
    """Build a contiguous, non-overlapping segment list against a window.

    Spec from issue #149:
      - `order_index` contiguous from 0
      - sorted by `order_index`, segments don't overlap
      - each segment fits in `[event_start, event_end]`
      - `location_index` is in `[0, location_count)`
    """
    if location_count <= 0:
        return st.just([])

    span_minutes = max(1, int((event_end - event_start).total_seconds() // 60))

    @st.composite
    def _build(draw):  # type: ignore[no-untyped-def]
        # Number of segments + how the window splits between them.
        count = draw(st.integers(min_value=1, max_value=max_count))
        # Pick `count` non-overlapping intervals by drawing N+1 cut points
        # in the window and pairing successive ones. Sort to keep order.
        cuts = sorted(
            draw(
                st.lists(
                    st.integers(min_value=0, max_value=span_minutes),
                    min_size=count + 1,
                    max_size=count + 1,
                    unique=True,
                ),
            ),
        )
        segments: list[SegmentRequest] = []
        for i in range(count):
            start = event_start + timedelta(minutes=cuts[i])
            end = event_start + timedelta(minutes=cuts[i + 1])
            if end <= start:
                # Cut points were equal — Hypothesis already enforces
                # uniqueness, but defensive guard for a degenerate draw.
                continue
            segments.append(
                SegmentRequest(
                    location_index=draw(st.integers(min_value=0, max_value=location_count - 1)),
                    order_index=i,
                    start_datetime=start,
                    end_datetime=end,
                    description=draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
                ),
            )
        return segments

    return _build()


def accessibility_filter() -> st.SearchStrategy[dict[str, bool | None]]:
    """A discovery accessibility filter, every flag independently tri-state."""
    flags = (
        "wheelchair",
        "accessible_restroom",
        "elevator",
        "seating",
        "captions",
        "quiet_friendly",
    )
    return st.fixed_dictionaries(
        {flag: st.one_of(st.none(), st.booleans()) for flag in flags},
    )
