"""Step 03 — Extract skills. Public entry point: run(state) -> state.

Runs the shared matcher over each posting's (HTML-stripped) content and stores the
canonical skill ids per posting.
"""

from app.pipeline_two.state import JobsRefreshState

from .logic import extract


async def run(state: JobsRefreshState) -> JobsRefreshState:
    assert state.filtered is not None  # set by step 02
    result = extract(state.filtered)
    return state.model_copy(update={"skills_by_job": result.skills_by_job})
