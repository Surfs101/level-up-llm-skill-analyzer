"""Step 01 — Fetch boards. Public entry point: run(state) -> state.

Fetches every allowlisted company's postings and stores them on the state.
"""

from app.pipeline_two.state import JobsRefreshState

from .logic import fetch


async def run(state: JobsRefreshState) -> JobsRefreshState:
    result = await fetch(state.companies)
    return state.model_copy(update={"fetched": result.fetched})
