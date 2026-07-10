"""Unit tests for PipelineState — construct, copy-with-update, immutability."""

import uuid

import pytest
from pydantic import ValidationError

from app.pipeline_one.state import PipelineState


def test_construct_with_inputs_leaves_derived_fields_none() -> None:
    state = PipelineState(run_id=uuid.uuid4(), jd_text="Backend role, Python + FastAPI")

    assert state.jd_text.startswith("Backend role")
    assert state.user_id is None
    assert state.is_guest is False
    # Nothing produced yet.
    assert state.resume_text is None
    assert state.missing_ids is None
    assert state.project_one_md is None


def test_model_copy_update_returns_new_state_without_mutating_original() -> None:
    original = PipelineState(run_id=uuid.uuid4(), jd_text="jd")

    updated = original.model_copy(update={"resume_text": "resume", "fit_score": 72})

    assert updated.resume_text == "resume"
    assert updated.fit_score == 72
    # The original is untouched — steps thread copies, they don't mutate.
    assert original.resume_text is None
    assert original.fit_score is None


def test_state_is_frozen() -> None:
    state = PipelineState(run_id=uuid.uuid4(), jd_text="jd")

    with pytest.raises(ValidationError):
        state.resume_text = "cannot assign in place"  # type: ignore[misc]
