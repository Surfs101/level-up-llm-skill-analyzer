# Step 02 — Extract text

**Purpose.** Turn the staged binary into clean plain text and drop the binary.

**Inputs (from state).** `r2_staging_key` and `file_hash` from step 01.

**Outputs (onto state).** `resume_text` (whitespace-normalized via
`app/nlp/text_clean.py`) and `r2_text_key` (the `.txt` written to a permanent,
content-addressed R2 key). The staging binary is deleted — no raw resume is kept (§11).

**Failure modes (§15).** The file won't parse, or parses to empty text (e.g. a
scanned PDF with no text layer) → `PipelineStepError` ("we couldn't read this
file — try re-saving as PDF").
