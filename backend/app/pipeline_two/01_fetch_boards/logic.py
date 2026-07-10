"""Step 01 logic — fetch every allowlisted board (design §9 step 1, §15).

A thin wrapper over app/greenhouse/client.py, which already does the 500ms spacing,
the 3-retry backoff, and — crucially — the per-company skip: a board that 5xxs or
rate-limits after retries is logged and skipped, the rest still fetch, and existing
data stays. So an empty or partial result is normal, never an error.
"""

from app.greenhouse.client import fetch_boards

from .schemas import FetchResult


async def fetch(companies: list[str]) -> FetchResult:
    postings = await fetch_boards(companies)
    return FetchResult(fetched=postings)
