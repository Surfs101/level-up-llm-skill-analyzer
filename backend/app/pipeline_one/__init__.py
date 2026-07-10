"""Pipeline 1 orchestrator (design §7, §8).

Tiny by design: an ordered list of the 8 step modules and a loop that imports each,
calls its run(state), and threads the returned state forward. Step directories start
with digits, so they're loaded by string name via importlib rather than a plain
import.

Between steps it bumps runs.current_stage so the polling UI advances. If a step
raises PipelineStepError (a user-facing §15 failure) the run is marked failed with
that message and the pipeline stops. An unexpected error also marks the run failed,
then re-raises so it surfaces (Sentry, Phase 6) — the worker runs with max_tries=1,
so a marked-failed run is not retried.

Authenticated path only. Guests carry is_guest but have no Postgres run row, so the
run-bookkeeping is skipped for them — the guest flow is Phase 6.
"""

import importlib

import logfire

from app.common.errors import PipelineStepError
from app.db.engine import get_sessionmaker
from app.db.redis import get_redis_client
from app.guest_runs import mark_guest_failed, set_guest_stage
from app.models import Run
from app.pipeline_one.state import PipelineState

STEP_MODULES = [
    "app.pipeline_one.01_ingest",
    "app.pipeline_one.02_extract_text",
    "app.pipeline_one.03_extract_skills",
    "app.pipeline_one.04_gap_analysis",
    "app.pipeline_one.05_retrieve_courses",
    "app.pipeline_one.06_select_courses",
    "app.pipeline_one.07_generate_projects",
    "app.pipeline_one.08_persist",
]

GENERIC_FAILURE = "Something went wrong while building your plan. Please try again."


async def run_pipeline(state: PipelineState) -> PipelineState:
    """Run all 8 steps in order, updating the run as it goes."""
    try:
        for stage_number, module_name in enumerate(STEP_MODULES, start=1):
            await _advance_stage(state, stage_number)
            step = importlib.import_module(module_name)
            # A span per step boundary: run_id / user_id / step, with latency from the
            # span's own timing (§12). No-op when Logfire has no token.
            with logfire.span(
                "pipeline_one.step {step}",
                step=module_name,
                stage=stage_number,
                run_id=str(state.run_id),
                user_id=str(state.user_id) if state.user_id else None,
            ):
                state = await step.run(state)
        return state
    except PipelineStepError as exc:
        # Expected, user-facing failure — the run row records it; no need to re-raise.
        await _mark_failed(state, exc.message)
        return state
    except Exception:
        await _mark_failed(state, GENERIC_FAILURE)
        raise  # unexpected — surface it; max_tries=1 keeps it from retrying


async def _advance_stage(state: PipelineState, stage_number: int) -> None:
    if state.is_guest:
        await set_guest_stage(get_redis_client(), state.run_id, stage_number)
        return
    async with get_sessionmaker()() as session:
        run = await session.get(Run, state.run_id)
        if run is None:
            return
        run.status = "running"
        run.current_stage = stage_number
        await session.commit()


async def _mark_failed(state: PipelineState, message: str) -> None:
    if state.is_guest:
        await mark_guest_failed(get_redis_client(), state.run_id, message)
        return
    async with get_sessionmaker()() as session:
        run = await session.get(Run, state.run_id)
        if run is None:
            return
        run.status = "failed"
        run.error_message = message
        await session.commit()
