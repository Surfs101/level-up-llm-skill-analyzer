"""Unit tests for the Greenhouse client — parse, allowlist (SSRF), retry, spacing.

httpx is mocked with MockTransport, so no network. asyncio.sleep is neutered so
tenacity backoff and the inter-company spacing don't actually wait.
"""

import asyncio

import httpx
import pytest

from app.greenhouse import client as greenhouse

PAYLOAD = {
    "jobs": [
        {
            "id": 123,
            "title": "Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
            "location": {"name": "Remote - US"},
            "content": "<p>Python and FastAPI</p>",
            "updated_at": "2026-06-01T12:00:00-04:00",
        },
        {
            "id": 456,
            "title": "Data Scientist",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/456",
            "location": None,
            "content": "<p>Machine learning</p>",
            "updated_at": "2026-06-02T09:00:00+00:00",
        },
    ]
}


class SequenceHandler:
    """A MockTransport handler that returns each response in turn, counting calls."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def client_for(handler: SequenceHandler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_parse_postings_maps_greenhouse_fields() -> None:
    postings = greenhouse.parse_postings("acme", PAYLOAD)

    assert len(postings) == 2
    first = postings[0]
    assert first.company == "acme"
    assert first.gh_job_id == "123"
    assert first.title == "Backend Engineer"
    assert first.location == "Remote - US"
    assert first.url.endswith("/jobs/123")
    assert "FastAPI" in first.content
    assert first.updated_at.year == 2026
    # A null location comes through as None, not a crash.
    assert postings[1].location is None


async def test_fetch_company_refuses_a_non_allowlisted_slug(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(greenhouse, "load_allowlist", lambda: frozenset({"acme"}))
    handler = SequenceHandler([httpx.Response(200, json=PAYLOAD)])

    async with client_for(handler) as client:
        with pytest.raises(greenhouse.DisallowedCompany):
            await greenhouse.fetch_company("evil-corp", client)

    assert handler.calls == 0  # refused before any request was made


async def test_fetch_company_returns_parsed_postings(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(greenhouse, "load_allowlist", lambda: frozenset({"acme"}))
    handler = SequenceHandler([httpx.Response(200, json=PAYLOAD)])

    async with client_for(handler) as client:
        postings = await greenhouse.fetch_company("acme", client)

    assert {p.gh_job_id for p in postings} == {"123", "456"}


async def test_fetch_retries_transient_errors_then_succeeds(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(greenhouse, "load_allowlist", lambda: frozenset({"acme"}))
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)  # skip backoff waits
    handler = SequenceHandler(
        [httpx.Response(500), httpx.Response(500), httpx.Response(200, json=PAYLOAD)]
    )

    async with client_for(handler) as client:
        postings = await greenhouse.fetch_company("acme", client)

    assert handler.calls == 3  # failed twice, third attempt succeeded
    assert len(postings) == 2


async def test_fetch_does_not_retry_a_404(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(greenhouse, "load_allowlist", lambda: frozenset({"acme"}))
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    handler = SequenceHandler([httpx.Response(404)])

    async with client_for(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await greenhouse.fetch_company("acme", client)

    assert handler.calls == 1  # a stale slug is a real answer, not retried


async def test_fetch_boards_spaces_companies_and_skips_failures(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(greenhouse, "load_allowlist", lambda: frozenset({"acme", "beta"}))
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)
    handler = SequenceHandler([httpx.Response(200, json=PAYLOAD)])

    async with client_for(handler) as client:
        postings = await greenhouse.fetch_boards(["acme", "beta"], client=client)

    # One 500ms gap between the two companies (none before the first).
    assert sleeps == [greenhouse.SPACING_SECONDS]
    assert len(postings) == 4  # both boards parsed


async def _no_sleep(_seconds: float) -> None:
    return None
