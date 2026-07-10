"""Greenhouse Job Board API client (design §9, §11).

Fetches public postings from boards-api.greenhouse.io. Two rules matter:

  - SSRF guard: we only ever fetch a company slug that appears in data/companies.json.
    A slug not on that allowlist is refused before any request is built — there is no
    path for a user-supplied slug or URL to reach httpx.
  - Politeness: 500ms between companies, and 3 tenacity retries with exponential
    backoff on transient errors (network, 429, 5xx). A 4xx like 404 (a stale slug) is
    NOT retried — it's logged and skipped, and the existing data stays (staleness is
    bounded by the 21-day window).

HTTP/2 is enabled: the many small GETs all hit one host, so they reuse a single
connection. (Needs the h2 package — the httpx[http2] extra.)
"""

import asyncio
import json
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# app/greenhouse/client.py -> parents[2] is backend/, where data/ lives.
_COMPANIES_PATH = Path(__file__).resolve().parents[2] / "data" / "companies.json"
_BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
SPACING_SECONDS = 0.5
_TIMEOUT = httpx.Timeout(10.0)


class GreenhousePosting(BaseModel):
    company: str
    gh_job_id: str
    title: str
    location: str | None
    url: str
    content: str  # raw HTML job description (fetched with content=true)
    updated_at: datetime  # Greenhouse's last-updated time; stored as posted_at downstream


class DisallowedCompany(ValueError):
    """A company slug that isn't on the allowlist — refused (the SSRF guard)."""


@lru_cache(maxsize=1)
def load_allowlist() -> frozenset[str]:
    """The company slugs we're allowed to fetch, from data/companies.json."""
    slugs: list[str] = json.loads(_COMPANIES_PATH.read_text())
    return frozenset(slugs)


async def fetch_boards(
    companies: list[str], client: httpx.AsyncClient | None = None
) -> list[GreenhousePosting]:
    """Fetch every company's postings, 500ms apart. A failing board is skipped.

    Pass `client` in tests; otherwise an HTTP/2 client is created and closed here.
    """
    own_client = client is None
    if client is None:
        client = httpx.AsyncClient(http2=True, timeout=_TIMEOUT)
    try:
        postings: list[GreenhousePosting] = []
        for index, company in enumerate(companies):
            if index > 0:
                await asyncio.sleep(SPACING_SECONDS)  # be polite between companies
            try:
                postings.extend(await fetch_company(company, client))
            except Exception as exc:  # one bad board doesn't sink the whole cycle
                logger.warning("skipping company %r this cycle: %s", company, exc)
        return postings
    finally:
        if own_client:
            await client.aclose()


async def fetch_company(company: str, client: httpx.AsyncClient) -> list[GreenhousePosting]:
    """Fetch and parse one board. Raises DisallowedCompany if it's not allowlisted."""
    if company not in load_allowlist():
        raise DisallowedCompany(company)
    response = await _get(client, _BOARD_URL.format(company=company))
    return parse_postings(company, response.json())


def parse_postings(company: str, payload: dict[str, Any]) -> list[GreenhousePosting]:
    """Turn a Greenhouse jobs payload into typed postings."""
    postings = []
    for job in payload.get("jobs", []):
        location = job.get("location") or {}
        postings.append(
            GreenhousePosting(
                company=company,
                gh_job_id=str(job["id"]),
                title=job["title"],
                location=location.get("name"),
                url=job["absolute_url"],
                content=job.get("content", ""),
                updated_at=datetime.fromisoformat(job["updated_at"]),
            )
        )
    return postings


def _is_retryable(exc: BaseException) -> bool:
    """Retry transient failures only — a 404/400 is a real answer, not a hiccup."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url)
    response.raise_for_status()
    return response
