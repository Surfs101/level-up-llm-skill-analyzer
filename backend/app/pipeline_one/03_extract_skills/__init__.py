"""Step 03 — Extract skills. Public entry point: run(state) -> state.

Runs the shared matcher over the resume text and the JD text and stores the two
canonical id lists. It does NOT fail on an empty result — the "no technical skills"
guard lives in step 04, which needs both sets to decide.
"""

from app.pipeline_one.state import PipelineState

from .logic import extract_skills


async def run(state: PipelineState) -> PipelineState:
    assert state.resume_text is not None  # set by step 02
    result = extract_skills(state.resume_text, state.jd_text)
    return state.model_copy(update=result.model_dump())
