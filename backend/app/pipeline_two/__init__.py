"""Pipeline 2 orchestrator (design §7, §9).

Tiny, mirroring Pipeline 1: an ordered list of the 5 step modules and a loop that
imports each (by string name, since the dirs start with digits) and threads the
returned state forward. There's no per-step DB bookkeeping — the jobs refresh has no
run row; it's a best-effort cron. If a step raises, it propagates to the task and Arq
records the job failure (max_tries=1).
"""

import importlib

import logfire

from app.pipeline_two.state import JobsRefreshState

STEP_MODULES = [
    "app.pipeline_two.01_fetch_boards",
    "app.pipeline_two.02_filter_recent",
    "app.pipeline_two.03_extract_skills",
    "app.pipeline_two.04_upsert",
    "app.pipeline_two.05_purge_old",
]


async def run_refresh(state: JobsRefreshState) -> JobsRefreshState:
    """Run all 5 steps in order: fetch → filter → extract → upsert → purge."""
    for module_name in STEP_MODULES:
        step = importlib.import_module(module_name)
        with logfire.span("pipeline_two.step {step}", step=module_name):  # no-op without a token
            state = await step.run(state)
    return state
