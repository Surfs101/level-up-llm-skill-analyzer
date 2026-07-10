"""Step 04 — Upsert. Public entry point: run(state) -> state.

Writes the filtered postings and their skills to Postgres, refreshing any that
already exist.
"""

from app.db.engine import get_sessionmaker
from app.pipeline_two.state import JobsRefreshState

from .logic import upsert


async def run(state: JobsRefreshState) -> JobsRefreshState:
    assert state.filtered is not None  # set by step 02
    assert state.skills_by_job is not None  # set by step 03
    async with get_sessionmaker()() as session:
        result = await upsert(session, state.filtered, state.skills_by_job)
    return state.model_copy(update={"upserted_count": result.upserted_count})
