"""Enqueue the jobs refresh (Pipeline 2) once, on demand.

The Greenhouse scrape normally runs on the worker's 6-hour cron, so a fresh
deploy has an empty /jobs feed until the first cron cycle. Run this once to
populate it now instead of waiting:

    uv run python scripts/trigger_jobs.py

It only enqueues the task — the worker process must be running to pick it up.
"""

import asyncio

from app.workers.queue import get_arq_pool


async def main() -> None:
    pool = await get_arq_pool()
    job = await pool.enqueue_job("refresh_jobs")
    print(f"Enqueued refresh_jobs (job id: {job.job_id}). The worker will run it shortly.")


if __name__ == "__main__":
    asyncio.run(main())
