"""Step 03 (extract skills) — real matcher over both texts; empty is not an error."""

import importlib
import uuid

from app.pipeline_one.state import PipelineState

skills_step = importlib.import_module("app.pipeline_one.03_extract_skills")


async def test_extracts_ids_from_both_texts() -> None:
    state = PipelineState(
        run_id=uuid.uuid4(),
        jd_text="We build with Python, Docker, and Kubernetes.",
        resume_text="Backend engineer experienced in Python and FastAPI.",
    )

    result = await skills_step.run(state)

    assert "python" in result.resume_skill_ids
    assert "fastapi" in result.resume_skill_ids
    assert {"python", "docker", "kubernetes"} <= set(result.jd_skill_ids)
    # Deterministic, sorted output.
    assert result.resume_skill_ids == sorted(result.resume_skill_ids)


async def test_no_skills_yields_empty_lists_not_an_error() -> None:
    state = PipelineState(
        run_id=uuid.uuid4(),
        jd_text="The quick brown fox jumps over the lazy dog.",
        resume_text="A hardworking team player who loves a challenge.",
    )

    result = await skills_step.run(state)

    # Step 03 never fails on emptiness — that's step 04's job.
    assert result.resume_skill_ids == []
    assert result.jd_skill_ids == []
