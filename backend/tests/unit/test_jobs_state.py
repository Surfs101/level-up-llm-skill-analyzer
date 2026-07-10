"""Unit tests for JobsRefreshState — construct, copy-with-update, immutability."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.greenhouse.client import GreenhousePosting
from app.pipeline_two.state import JobsRefreshState


def a_posting() -> GreenhousePosting:
    return GreenhousePosting(
        company="acme",
        gh_job_id="123",
        title="Backend Engineer",
        location="Remote - US",
        url="https://boards.greenhouse.io/acme/jobs/123",
        content="<p>Python</p>",
        updated_at=datetime(2026, 6, 1, 12, 0, 0),
    )


def test_construct_with_companies_leaves_derived_fields_none() -> None:
    state = JobsRefreshState(companies=["acme", "beta"])

    assert state.companies == ["acme", "beta"]
    assert state.fetched is None
    assert state.filtered is None
    assert state.skills_by_job is None
    assert state.upserted_count is None
    assert state.purged_count is None


def test_model_copy_update_returns_new_state_without_mutating_original() -> None:
    original = JobsRefreshState(companies=["acme"])

    updated = original.model_copy(
        update={
            "fetched": [a_posting()],
            "skills_by_job": {"acme/123": ["python"]},
            "upserted_count": 1,
            "purged_count": 3,
        }
    )

    assert updated.fetched is not None and updated.fetched[0].gh_job_id == "123"
    assert updated.skills_by_job == {"acme/123": ["python"]}
    assert updated.upserted_count == 1 and updated.purged_count == 3
    # The original is untouched — steps thread copies, they don't mutate.
    assert original.fetched is None
    assert original.upserted_count is None


def test_state_is_frozen() -> None:
    state = JobsRefreshState(companies=["acme"])
    with pytest.raises(ValidationError):
        state.purged_count = 5  # type: ignore[misc]
