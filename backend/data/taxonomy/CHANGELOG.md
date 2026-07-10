# Taxonomy CHANGELOG

Audit trail of every change to the canonical skill taxonomy. `skills.json` is
generated — never hand-edited. See **Maintenance** at the bottom for the edit
workflow.

---

## 2026-06-09 — Phase 1 alias cleanup (overly-generic drops)

Building a synthetic F1 corpus surfaced six aliases that are ordinary English
words and fire false positives on normal prose. Added them to a new
`OVERLY_GENERIC_ALIAS_DROPS` constant in `build_taxonomy.py` (dropped at build
time; the validator in `generate_aliases.py` can't catch these because they
collide with nothing in the taxonomy):

| dropped alias | was mapped to | false positive |
|---|---|---|
| `be` | Berry | "should **be** comfortable" |
| `do` | DigitalOcean | "to **do**", everywhere |
| `batch` | Batchfile | "**batch** processing" (its own technique) |
| `glue` | AWS Glue | "**glue** code" |
| `teams` | Microsoft Teams | "cross-functional **teams**" |
| `cake` | C# | stale seed alias; Cake is a build tool, not C# |

Multi-word forms (`aws glue`, `microsoft teams`, `ms teams`) are kept. Aliases
1,286 → 1,280. Integrity green; `build_taxonomy.py --check` exits 0.

---

## 2026-06-09 — Phase 1 bulk alias generation

Ran `scripts/generate_aliases.py` (gpt-4o-mini, temperature 0, batches of 25)
over the 817 eligible raw-origin entries — those with 0 aliases, or 1 alias on a
name with likely variants — skipping obscure short language names and the 67
non-raw entries (techniques + code-defined canonicals) whose aliases live in
`build_taxonomy.py`.

- **944 aliases accepted**, taking the taxonomy from **342 → 1,286 aliases**.
- Every generated alias was validated against the full taxonomy before
  acceptance: dropped if it equalled any canonical name, id, or existing alias
  (of any entry), its own canonical/id, contained disallowed characters, was
  < 2 chars, or duplicated another alias generated this run. This is why all 11
  integrity assertions stay green and `build_taxonomy.py --check` still exits 0.
- High-value surface forms that previously did not match now resolve, e.g.
  `postgres → postgresql`, `fast api → fastapi`, `k8s → kubernetes`,
  `nextjs → next-js`, `react.js → react`, `golang → go`.

**Provenance / source-of-truth note:** accepted aliases were written back into
`skills_raw.json` so the build stays idempotent (it rebuilds aliases from raw).
This is a *programmatic, validated* update with a full audit trail in
`data/taxonomy/aliases_generated.json` (every accepted + every rejected alias
with its reason) — not a hand-edit. The "raw is pristine" rule below still holds
for humans: raw is only ever touched by this reviewed script, never by hand.

---

## 2026-06-09 — Phase 0 initial build

First transform of `skills_raw.json` (1,014 pristine seed entries) into
`skills.json` (1,095 canonical skills) via `scripts/build_taxonomy.py`. All 11
assertions in `tests/unit/test_taxonomy_integrity.py` pass; the build is
idempotent (a second run produces a byte-identical file).

### Slug ids added

Every entry received a stable lowercase slug `id` derived from its
`canonical_name`:

- Look up `SLUG_OVERRIDES` first; if absent, lowercase → replace `&` with `and`
  → replace each run of characters outside `[a-z0-9]` with `-` → collapse
  repeated `-` → strip leading/trailing `-`.
- On a slug collision, append `-<category>`; if still colliding, the build errors
  out. (No collisions occurred in this build.)

Overrides used (names the general rule would mangle):

| canonical_name | id |
|---|---|
| .NET | `dotnet` |
| .NET Framework | `dotnet-framework` |
| .NET MAUI | `dotnet-maui` |
| C++ | `cpp` |
| C# | `csharp` |
| F# | `fsharp` |
| F* | `fstar` |
| Q# | `qsharp` |
| Objective-C++ | `objective-cpp` |

### priority_rank injected

Each entry's `priority_rank` was set from its category via
`categories.json`: `language` → 1, `framework` → 2,
`library`/`database`/`cloud`/`devops`/`tool` → 3, `technique` → 4.

### Technique category added (80 entries)

The `technique` category did not exist in the seed. 79 entries were added, and
`RAG` was recategorized into it (see below) for 80 total:

A/B Testing, Agile, Anomaly Detection, API Design, Authentication, Authorization,
Backend Development, Batch Processing, Behavior-Driven Development, Caching,
CI/CD, Classification, Cloud Computing, Clustering, Computer Vision,
Containerization, Cryptography, Data Analysis, Data Engineering, Data Modeling,
Data Science, Data Visualization, Database Design, DataOps, Deep Learning,
DevOps, Distributed Systems, Domain-Driven Design, ELT, Embeddings, Encryption,
End-to-End Testing, ETL, Event Streaming, Event-Driven Architecture, Feature
Engineering, Fine-tuning, Frontend Development, Full-Stack Development, Functional
Programming, Generative AI, Integration Testing, Kanban, Large Language Models,
Load Balancing, Load Testing, Logging, Machine Learning, Microservices, MLOps,
Mobile Development, Monitoring, Monorepo, Multi-factor Authentication, Natural
Language Processing, Object-Oriented Programming, Observability, Performance
Optimization, Predictive Modeling, Prompt Engineering, RAG, Recommendation
Systems, Regression, Reinforcement Learning, Scrum, Security Testing, Semantic
Search, Serverless Architecture, Single Sign-On, Site Reliability Engineering,
Statistical Analysis, Stream Processing, System Design, Test-Driven Development,
Threat Modeling, Time Series Analysis, Unit Testing, Vector Search, Web
Development, Web Scraping.

### Missing canonicals added (5 entries)

| canonical_name | category | seed aliases |
|---|---|---|
| C | language | clang |
| R | language | rlang, r-lang |
| Octave | language | — |
| Pandoc | tool | — |
| OpenTofu | devops | — (see alias note below) |

### Recategorized

- **RAG**: `tool` → `technique` (existing aliases `retrieval-augmented
  generation`, `retrieval augmented generation` kept).

### Merged duplicates

Each merge keeps the first entry and deletes the second, folding any unique
aliases into the kept one:

- **Eclipse** + Eclipse IDE → kept **Eclipse**.
- **Jenkins** + Jenkins CI → kept **Jenkins**.
- **Spring Framework** + Spring → kept **Spring Framework** (bare "Spring"
  deleted; "Spring Boot" remains a separate entry).

### Alias collisions dropped (21 total)

**Cross-entry collisions (13)** — the alias really belongs to a different
entry's canonical/id:

| alias | dropped from | belongs to |
|---|---|---|
| node | JavaScript | Node.js |
| terraform | HCL | Terraform |
| opentofu | HCL | OpenTofu |
| bash | Shell | Bash |
| shell-script | Shell | Shell script |
| lisp | Common Lisp | Lisp |
| emacs | Emacs Lisp | Emacs |
| delphi | Pascal | Delphi |
| octave | MATLAB | Octave |
| pandoc | Markdown | Pandoc |
| make | Makefile | Make |
| vim | Vim Script | Vim |
| visual basic | Visual Basic .NET | ambiguous between the two Visual Basic entries |

**Redundant self-aliases (8)** — the alias equals its own entry's id/canonical
(the matcher already matches canonical names), so it is removed automatically:

| alias | dropped from | reason |
|---|---|---|
| csharp | C# | == id `csharp` |
| cpp | C++ | == id `cpp` |
| fsharp | F# | == id `fsharp` |
| fstar | F* | == id `fstar` |
| qsharp | Q# | == id `qsharp` |
| framer-motion | Framer Motion | == id `framer-motion` |
| material-ui | Material UI | == id `material-ui` |
| opentofu | OpenTofu | == id/canonical `opentofu` (the step-E seed alias) |

> Note: the defensive drop of `visual basic` from "Visual Basic 6.0" was a no-op
> (that entry never carried the bare alias). Dropping `csharp`/`cpp`/etc. means
> those exact surface forms are not matchable as aliases while they equal the id;
> revisit those slug choices in Phase 1 if matchability is wanted.

### Final counts

- **Total canonicals: 1,095**
- **Total aliases: 342**

| category | priority_rank | count |
|---|---|---|
| language | 1 | 547 |
| framework | 2 | 55 |
| library | 3 | 75 |
| database | 3 | 45 |
| cloud | 3 | 42 |
| devops | 3 | 50 |
| tool | 3 | 201 |
| technique | 4 | 80 |

---

## Maintenance

The taxonomy is never "done", but `skills.json` is **generated** — treat it as a
build artifact.

To change the taxonomy:

1. **Edit `scripts/build_taxonomy.py`**, not `skills.json`. New skills, alias
   fixes, merges, slug overrides, and collision drops all live in the named
   constants at the top of that script (`SLUG_OVERRIDES`, `TECHNIQUE_ENTRIES`,
   `MISSING_CANONICALS`, `MERGES`, `CROSS_ENTRY_ALIAS_DROPS`). The raw seed
   `skills_raw.json` must never be hand-edited. The one sanctioned writer to raw
   is `scripts/generate_aliases.py`, which appends machine-generated, validated
   aliases with a full audit trail (`aliases_generated.json`) — see the
   2026-06-09 Phase 1 entry above.
2. **Re-run the build:** `uv run python scripts/build_taxonomy.py`.
3. **Ensure the integrity tests pass:**
   `uv run pytest tests/unit/test_taxonomy_integrity.py`. If a test surfaces a
   new collision or bad slug, fix it in the script (extend `SLUG_OVERRIDES` or
   `CROSS_ENTRY_ALIAS_DROPS`) and re-run until green.
4. **Confirm idempotency:** `uv run python scripts/build_taxonomy.py --check`
   must exit 0.
5. **Append a dated entry to this CHANGELOG** describing what changed and why.

`app/nlp/audit.py` (built in a later phase) surfaces high-frequency unmatched
skill-shaped tokens from real resumes/JDs as candidate additions — run it
monthly, review by hand, then follow the workflow above.
