"""Step 01 (fetch boards) — stores fetched postings; empty is fine.

The per-company skip on 5xx/rate-limit is `fetch_boards`'s job (covered in
tests/unit/test_greenhouse_client.py); here we just check the step wires it onto state.
"""

import importlib

from app.pipeline_two.state import JobsRefreshState

fetch_step = importlib.import_module("app.pipeline_two.01_fetch_boards")
fetch_logic = importlib.import_module("app.pipeline_two.01_fetch_boards.logic")


async def test_run_stores_fetched_postings(make_posting, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    postings = [make_posting(gh_job_id="1"), make_posting(gh_job_id="2")]

    async def fake_fetch_boards(_companies: list[str]) -> list:  # type: ignore[type-arg]
        return postings

    monkeypatch.setattr(fetch_logic, "fetch_boards", fake_fetch_boards)

    new_state = await fetch_step.run(JobsRefreshState(companies=["test-acme"]))

    assert new_state.fetched == postings


async def test_empty_board_yields_empty_fetched(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_fetch_boards(_companies: list[str]) -> list:  # type: ignore[type-arg]
        return []

    monkeypatch.setattr(fetch_logic, "fetch_boards", fake_fetch_boards)

    new_state = await fetch_step.run(JobsRefreshState(companies=["test-acme"]))

    assert new_state.fetched == []
