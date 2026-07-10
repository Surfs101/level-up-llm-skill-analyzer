# JD fixtures

Drop anonymized job-description `.txt` files here, plus an optional
`<name>.expected.json` next to each one listing the canonical skill IDs the
matcher should extract. Used to measure matcher F1 in phase 1 and to drive the
Pipeline 1 e2e test.

## Current contents (2026-06-09) — SYNTHETIC

The 10 `*.txt` here are **hand-authored synthetic job descriptions**, not real
postings. Same purpose and caveat as the resume fixtures: a sanity-check corpus
for matcher F1, to be replaced by real anonymized JDs.
