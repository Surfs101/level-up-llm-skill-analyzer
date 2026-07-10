# Resume fixtures

Drop anonymized `.txt` resumes here, plus an optional `<name>.expected.json`
next to each one listing the canonical skill IDs the matcher should extract.
Used to measure matcher F1 in phase 1 and to drive the Pipeline 1 e2e test.

## Current contents (2026-06-09) — SYNTHETIC

The 11 `*.txt` here are **hand-authored synthetic resumes**, not real people.
They use realistic messy surface forms (`postgres`, `k8s`, `react.js`, `golang`,
`ci/cd`) to exercise the matcher, with `*.expected.json` labels authored by
reading each text independently of the matcher. They give a sanity-check F1
(~0.99), not the objective external-data measure — drop real anonymized resumes
here to replace them.
