# Step 01 — Ingest

**Purpose.** Accept the uploaded resume and validate it before any work happens.

**Inputs (from state).** `file_bytes` (the raw upload) and `run_id`.

**Outputs (onto state).** `file_hash` (sha256, for dedupe), `r2_staging_key` (the
binary staged to a temporary R2 key). Clears `file_bytes` — it's in R2 now.

**Failure modes (§15).** Over 5 MB → reject before reading further. Not a real
PDF/DOCX by magic-byte check (`app/common/files.py`, not the declared type) → reject.
Both raise `PipelineStepError` with a friendly message.
