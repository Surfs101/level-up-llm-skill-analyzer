# Step 03 — Extract skills

**Purpose.** Tag each posting with canonical skill ids using the **same** matcher as
Pipeline 1, so job scoring is symmetric with analysis scoring.

**Inputs (from state).** `filtered` from step 02.

**Outputs (onto state).** `skills_by_job` — canonical skill ids per posting, keyed
`"company/gh_job_id"`. Each posting's HTML is stripped to text
(`app/common/html.py`) and run through the shared `app/nlp/matcher.py`.

**Failure modes.** A posting that matches zero skills gets an empty list — it's still
stored (step 04) and simply ranks low on overlap; nothing fails.
