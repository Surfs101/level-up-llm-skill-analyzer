# Step 05 — Retrieve courses

**Purpose.** Find the courses most relevant to the candidate's skill gap (RAG).

**Inputs (from state).** `missing_ids` — the priority-sorted missing skills from
step 04.

**Outputs (onto state).** `retrieved_course_ids` — up to 50 candidate course ids.
A query string is built from the missing skills' display names, embedded with
`text-embedding-3-small`, and matched by `pgvector` cosine over the HNSW index. All
of that lives in `app/rag/retriever.py`; this step just calls it and keeps the ids.

**Failure modes.** OpenAI embedding error → retried with backoff, then the run
fails. Fewer than 2 usable candidates is handled downstream in step 06.
