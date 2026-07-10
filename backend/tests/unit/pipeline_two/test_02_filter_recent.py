"""Step 02 (filter recent) — recency window + US/Canada location heuristic."""

import importlib
from datetime import UTC, datetime, timedelta

filter_logic = importlib.import_module("app.pipeline_two.02_filter_recent.logic")

NOW = datetime(2026, 7, 1, tzinfo=UTC)


def test_keeps_recent_us_ca_drops_old_and_foreign(make_posting) -> None:  # type: ignore[no-untyped-def]
    recent_us = make_posting(
        gh_job_id="1", location="San Francisco, CA", updated_at=NOW - timedelta(days=5)
    )
    recent_ca = make_posting(
        gh_job_id="2", location="Toronto, ON", updated_at=NOW - timedelta(days=1)
    )
    old_us = make_posting(
        gh_job_id="3", location="Remote - US", updated_at=NOW - timedelta(days=30)
    )
    foreign = make_posting(gh_job_id="4", location="London, United Kingdom", updated_at=NOW)
    no_location = make_posting(gh_job_id="5", location=None, updated_at=NOW)

    result = filter_logic.filter_recent(
        [recent_us, recent_ca, old_us, foreign, no_location], now=NOW
    )

    assert {p.gh_job_id for p in result.filtered} == {"1", "2"}


def test_location_heuristic() -> None:
    assert filter_logic.is_us_or_canada("Remote - US")
    assert filter_logic.is_us_or_canada("New York, NY")
    assert filter_logic.is_us_or_canada("Austin, TX")
    assert filter_logic.is_us_or_canada("Vancouver, British Columbia, Canada")
    assert filter_logic.is_us_or_canada("Toronto, ON")
    assert not filter_logic.is_us_or_canada("London, United Kingdom")
    assert not filter_logic.is_us_or_canada("Berlin, Germany")
    assert not filter_logic.is_us_or_canada(None)


def test_21_day_boundary(make_posting) -> None:  # type: ignore[no-untyped-def]
    just_inside = make_posting(
        gh_job_id="in", location="Remote - US", updated_at=NOW - timedelta(days=20, hours=23)
    )
    just_outside = make_posting(
        gh_job_id="out", location="Remote - US", updated_at=NOW - timedelta(days=21, seconds=1)
    )

    result = filter_logic.filter_recent([just_inside, just_outside], now=NOW)

    assert {p.gh_job_id for p in result.filtered} == {"in"}
