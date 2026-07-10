# Step 04 — Upsert

**Purpose.** Persist the postings and their skills idempotently.

**Inputs (from state).** `filtered` (step 02) and `skills_by_job` (step 03).

**Outputs (onto state).** `upserted_count`. Each `job_postings` row is upserted on
`(company, gh_job_id)` (insert or refresh); its `job_skills` rows are fully replaced
to match the freshly extracted skill set. `jd_text` is the HTML-stripped posting text.

**Failure modes.** The whole batch commits in one transaction; a DB error aborts the
cycle and is retried next cycle (existing data stays).
