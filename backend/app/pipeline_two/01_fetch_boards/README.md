# Step 01 — Fetch boards

**Purpose.** Pull current job postings from every tracked Greenhouse board.

**Inputs (from state).** `companies` — the allowlisted slugs.

**Outputs (onto state).** `fetched` — the raw postings across all boards. Fetching
lives in `app/greenhouse/client.py`: 500 ms between companies, 3-retry backoff, HTTP/2.

**Failure modes (§15).** A company that 5xxs / rate-limits after retries is logged and
skipped this cycle; the rest still fetch and existing data stays. A partial or empty
result is normal, not an error.
