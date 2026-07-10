"""Step 05 — Purge old. Public entry point: run(state) -> state.

Deletes postings older than the 21-day window and records how many went.
"""

from app.db.engine import get_sessionmaker
from app.pipeline_two.state import JobsRefreshState

from .logic import purge


async def run(state: JobsRefreshState) -> JobsRefreshState:
    async with get_sessionmaker()() as session:
        result = await purge(session)
    return state.model_copy(update={"purged_count": result.purged_count})
