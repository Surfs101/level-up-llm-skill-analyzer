# Step 05 — Purge old

**Purpose.** Drop postings past their freshness window so `/jobs` stays bounded.

**Inputs (from state).** None — operates on the `job_postings` table directly.

**Outputs (onto state).** `purged_count`. Deletes `job_postings` with
`posted_at < now - 21 days` (cascading to `job_skills`).

**Failure modes.** None expected; a failed delete just leaves stale rows, which the
21-day window in `GET /jobs` excludes from reads anyway.
