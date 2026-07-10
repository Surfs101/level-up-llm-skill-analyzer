"""Step 07 — Generate projects. Public entry point: run(state) -> state.

Renders the two prompts from the state and generates both projects with parallel
gpt-4o calls. Sets project_one_md and project_two_md.
"""

from app.pipeline_one.state import PipelineState

from .logic import generate_projects


async def run(state: PipelineState) -> PipelineState:
    assert state.matched_ids is not None  # set by step 04
    course_a_covered = state.course_a_covered or []  # set by step 06 (may be empty)
    result = await generate_projects(
        state.matched_ids, state.jd_text, course_a_covered, run_id=state.run_id
    )
    return state.model_copy(update=result.model_dump())
