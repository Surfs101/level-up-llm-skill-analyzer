"""The 6-hour jobs cron is registered and points at refresh_jobs."""

from app.workers.settings import WorkerSettings
from app.workers.tasks import refresh_jobs


def test_jobs_cron_registered_every_six_hours() -> None:
    crons = WorkerSettings.cron_jobs
    assert len(crons) == 1

    job = crons[0]
    assert job.coroutine.__name__ == "refresh_jobs"
    assert job.hour == {0, 6, 12, 18}  # every 6 hours
    assert job.minute == {0} or job.minute == 0


async def test_refresh_jobs_runs_the_orchestrator(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.workers import tasks

    seen = {}

    async def fake_run_refresh(state) -> object:  # type: ignore[no-untyped-def]
        seen["companies"] = state.companies
        return state

    monkeypatch.setattr(tasks, "run_refresh", fake_run_refresh)
    monkeypatch.setattr(tasks, "load_allowlist", lambda: frozenset({"stripe", "figma"}))

    await refresh_jobs({})

    assert seen["companies"] == ["figma", "stripe"]  # sorted allowlist
