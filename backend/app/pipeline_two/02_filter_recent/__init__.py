"""Step 02 — Filter recent. Public entry point: run(state) -> state.

Keeps postings that are recent (≤ 21 days) and located in the US or Canada.
"""

from app.pipeline_two.state import JobsRefreshState

from .logic import filter_recent


async def run(state: JobsRefreshState) -> JobsRefreshState:
    assert state.fetched is not None  # set by step 01
    result = filter_recent(state.fetched)
    return state.model_copy(update={"filtered": result.filtered})
