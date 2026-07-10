"""Step 06 — Select courses. Public entry point: run(state) -> state.

Reloads the retrieved candidates, picks the two best for the gap, and stores their
ids plus the missing skills each one covers (which step 07 uses to build projects).
"""

from app.db.engine import get_sessionmaker
from app.pipeline_one.state import PipelineState

from .logic import choose_courses


async def run(state: PipelineState) -> PipelineState:
    assert state.retrieved_course_ids is not None  # set by step 05
    assert state.missing_ids is not None  # set by step 04
    async with get_sessionmaker()() as session:
        result = await choose_courses(session, state.retrieved_course_ids, state.missing_ids)
    return state.model_copy(update=result.model_dump())
