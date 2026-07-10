"""Arq worker configuration — the `arq app.workers.settings.WorkerSettings` process.

Registers the pipeline task, the 6-hour jobs cron, and points at the same Redis the
API enqueues to. Runs are deterministic, so a failed job isn't worth retrying
(max_tries=1).
"""

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.observability import configure_observability
from app.workers.tasks import refresh_jobs, run_pipeline_one


async def _on_startup(_ctx: dict[str, object]) -> None:
    configure_observability("skillbridge-worker")  # Logfire + Sentry (no-op without secrets)


class WorkerSettings:
    functions = [run_pipeline_one]
    # Pipeline 2 (jobs) refresh, every 6 hours on the hour.
    cron_jobs = [cron(refresh_jobs, hour={0, 6, 12, 18}, minute=0, run_at_startup=False)]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 1
    on_startup = _on_startup
