"""Step 08 — Persist. Public entry point: run(state) -> state.

Terminal step (returns the state unchanged). For a signed-in user it writes the Plan
row and completes the run; for a guest it writes the plan into their Redis run record.
"""

from app.db.engine import get_sessionmaker
from app.pipeline_one.state import PipelineState

from .logic import persist, persist_guest


async def run(state: PipelineState) -> PipelineState:
    if state.is_guest:
        await persist_guest(state)
        return state
    async with get_sessionmaker()() as session:
        await persist(session, state)
    return state
