"""Step 04 (gap analysis) — matched/missing/fit, and the §15 zero-skills failure."""

import importlib
import uuid

import pytest

from app.common.errors import PipelineStepError
from app.pipeline_one.state import PipelineState

gap_step = importlib.import_module("app.pipeline_one.04_gap_analysis")


def make_state(resume_ids: list[str], jd_ids: list[str]) -> PipelineState:
    return PipelineState(
        run_id=uuid.uuid4(),
        jd_text="a job description",
        resume_skill_ids=resume_ids,
        jd_skill_ids=jd_ids,
    )


async def test_matched_missing_and_fit_score() -> None:
    state = make_state(
        resume_ids=["python", "docker"],
        jd_ids=["python", "fastapi", "docker", "kubernetes"],
    )

    result = await gap_step.run(state)

    assert result.matched_ids == ["docker", "python"]  # sorted intersection
    # missing sorted by priority_rank: fastapi (framework, 2) before kubernetes (devops, 3)
    assert result.missing_ids == ["fastapi", "kubernetes"]
    assert result.fit_score == 50  # round(100 * 2/4)


async def test_empty_resume_skills_fails_the_run() -> None:
    with pytest.raises(PipelineStepError, match="technical skills"):
        await gap_step.run(make_state(resume_ids=[], jd_ids=["python"]))


async def test_empty_jd_skills_fails_the_run() -> None:
    with pytest.raises(PipelineStepError, match="technical skills"):
        await gap_step.run(make_state(resume_ids=["python"], jd_ids=[]))
