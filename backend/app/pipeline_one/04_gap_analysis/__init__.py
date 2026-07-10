"""Step 04 — Gap analysis. Public entry point: run(state) -> state.

Compares the resume and JD skill sets into matched/missing and a fit score. Fails
the run if either side has no skills (design §15).
"""

from app.pipeline_one.state import PipelineState

from .logic import analyze_gap


async def run(state: PipelineState) -> PipelineState:
    assert state.resume_skill_ids is not None  # set by step 03
    assert state.jd_skill_ids is not None  # set by step 03
    result = analyze_gap(state.resume_skill_ids, state.jd_skill_ids)
    return state.model_copy(update=result.model_dump())
