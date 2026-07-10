"""Step 05 — Retrieve courses. Public entry point: run(state) -> state.

Opens a DB session, retrieves the cosine-nearest course candidates for the gap, and
stores their ids on the state.
"""

from app.db.engine import get_sessionmaker
from app.pipeline_one.state import PipelineState

from .logic import retrieve


async def run(state: PipelineState) -> PipelineState:
    assert state.missing_ids is not None  # set by step 04
    async with get_sessionmaker()() as session:
        result = await retrieve(session, state.missing_ids)
    return state.model_copy(update=result.model_dump())
