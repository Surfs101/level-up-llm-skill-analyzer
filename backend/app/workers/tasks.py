"""Arq task entry points.

run_pipeline_one is enqueued by POST /analyze. It carries the inputs the pipeline
needs — the uploaded bytes and the JD text — because they aren't persisted anywhere
the worker could otherwise read by run_id alone (the raw upload is never stored; the
JD lives only in the eventual Plan). The task loads the run for its user_id, builds
the initial PipelineState, and hands off to the orchestrator.
"""

import uuid

from app.db.engine import get_sessionmaker
from app.greenhouse.client import load_allowlist
from app.models import Run
from app.pipeline_one import run_pipeline
from app.pipeline_one.state import PipelineState
from app.pipeline_two import run_refresh
from app.pipeline_two.state import JobsRefreshState


async def run_pipeline_one(
    ctx: dict[str, object],
    run_id: str,
    file_bytes: bytes,
    jd_text: str,
    filename: str | None = None,
    is_guest: bool = False,
) -> None:
    run_uuid = uuid.UUID(run_id)

    user_id = None
    if not is_guest:
        # Signed-in runs have a Run row that carries the user_id. Guests have none.
        async with get_sessionmaker()() as session:
            run = await session.get(Run, run_uuid)
            if run is None:
                return  # run was deleted before the worker picked it up
            user_id = run.user_id

    state = PipelineState(
        run_id=run_uuid,
        user_id=user_id,
        is_guest=is_guest,
        jd_text=jd_text,
        filename=filename,
        file_bytes=file_bytes,
    )
    await run_pipeline(state)


async def refresh_jobs(ctx: dict[str, object]) -> None:
    """The 6-hour jobs cron: refresh every allowlisted board's postings."""
    state = JobsRefreshState(companies=sorted(load_allowlist()))
    await run_refresh(state)
