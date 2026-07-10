# SkillBridge 2.0 — Backend Checkpoint

_Last updated: 2026-07-07_

Where we stopped, what's real, and what's next. The full architecture lives in
[`skillbridge-backend-design.md`](./skillbridge-backend-design.md); this file is
the "you are here" marker against that plan's build order (§17).

---

## TL;DR

**All 6 phases are done — the backend is feature-complete and deploy-ready.** Both
pipelines run end to end (Pipeline 1: `POST /analyze` → 8-step Arq job → immutable
`Plan`; Pipeline 2: 6-hour Greenhouse cron → `GET /jobs` per-user overlap ranking).
Phase 6 hardening is in: the **guest analysis path** (Redis-only, 1h TTL, plan inline),
**rate limits** (guest 5/24h, authed 20/day, per-IP `/auth`) + **CSRF** double-submit,
**observability** (Logfire + Sentry no-op-safe, cost-ledger, deep `/healthz`+`/readyz`),
the **F5 resume→dashboard merge**, and the **Railway/Docker deploy config** (image builds,
both services boot). What's left is the human deploy runbook (provisioning, DNS, secrets)
and the product-polish punch-list below.

Test status: `uv run pytest -q` → **170 passed** with the DB up (0 skipped);
fewer with no DB/Redis (the skips are the Postgres-backed integration tests; unit tests —
matcher, ranker, sessions, LLM client, both pipelines' steps, Greenhouse client, project
generation, rate-limit/CSRF, observability — run everywhere via mocks/fakeredis/moto).

---

## How we build the backend

The shape of the system and the way we divide the work. Read this before picking
up a new phase — it's the "rules of the road."

### The architecture in one picture

One Python codebase, one Docker image, deployed as **two Railway services** with
different start commands:

- **`web`** — a FastAPI process serving all HTTP (`uvicorn app.main:app`).
- **`worker`** — one Arq process running both pipelines off Redis
  (`arq app.workers.settings.WorkerSettings`), plus a 6-hour cron for jobs.

Backing services: **Postgres 16 + pgvector** (everything relational + the 5K
course vectors — no separate vector DB), **Redis** (task queue, OAuth sessions,
guest run state, rate limits — one Redis, four jobs), **Cloudflare R2** (resume
`.txt` files only). External: OpenAI, Google OAuth, Greenhouse.

The app tier is **stateless** — sessions and rate limits live in Redis, files in
R2 — so any replica is interchangeable. This is deliberately small: ~15K lifetime
analyses, ~50/day peak. No microservices, no Kubernetes, no read replicas.

### The one invariant everything rides on

**Every skill enters the system through exactly one matcher, backed by exactly one
source of truth.**

- One place skills are extracted from text: `app/nlp/matcher.py`.
- One source of truth for what a skill *is*: `data/taxonomy/skills.json`.
- Every skill is a stable slug `id` (`fastapi`, `node-js`, `machine-learning`)
  that is the foreign key everywhere downstream — user skills, course skills, job
  skills, and inside every saved plan.

A surface string is never stored where an `id` belongs. Both pipelines share the
same matcher, so extraction is symmetric — a resume, a JD, and a job posting are
all reduced to the same id space, which is what makes scoring meaningful. This
invariant is *why* the taxonomy and matcher were built first and hardest.

### How the work is divided — phases

The build runs as **6 scope-limited phases** (design §17), done in order because
each depends on the one before:

```
Phase 0  Setup + taxonomy         ✅ done
Phase 1  Aliases + matcher        ✅ done   ← load-bearing
Phase 2  Course corpus + RAG      ✅ done
Phase 3  Auth + dashboard         ✅ done
Phase 4  Pipeline 1 (analysis)    ✅ done
Phase 5  Pipeline 2 (jobs)        ✅ done
Phase 6  Polish + deploy          ✅ done (code; human runbook remains)
```

Each phase is one focused chunk of work, and each is **gated by a read-only
checkpoint** before the next begins: lint (`ruff`), types (`mypy`), tests
(`pytest`), and the phase's own done-criteria all have to pass. We don't start the
next phase on top of a broken one.

**Load-bearing parts are built test-first.** The taxonomy integrity test existed
before the data transform; the matcher was held to an F1 target on a hand-labeled
corpus before anything consumed it. Foundations get proven before we build on them.

### How the work is divided — inside a pipeline

Both pipelines follow the same **step-module convention** (design §7). Each step is
a self-contained *directory*, not a file:

```
app/pipeline_one/04_gap_analysis/
  __init__.py     exposes exactly one callable: async def run(state) -> state
  logic.py        the implementation (private to the step)
  schemas.py      this step's own Pydantic in/out models
  README.md       purpose, inputs, outputs, failure modes
  prompts/        only on steps that call an LLM (e.g. 07_generate_projects)
```

The contract:

- **One public callable per step:** `run(state)`. The orchestrator only ever calls
  `run()`; everything else in the directory is private to the step.
- **State is threaded, not global.** A single typed `PipelineState`
  (`pipeline_one/state.py`) is passed in, and each step returns an updated copy.
  Every step is independently testable with a hand-built state fixture.
- **The orchestrator is tiny:** an ordered list of step module names and a loop
  that imports each, calls `run(state)`, and updates `runs.current_stage` so the
  polling UI advances. (Step dirs start with digits for ordering, so they're loaded
  by string name via `importlib` rather than a plain `import`.)
- **Tests mirror the steps** under `tests/unit/pipeline_one/test_0N_*.py` — they
  don't sit next to the code, which keeps `app/` import-clean.

This is what lets us build a pipeline one step at a time, each with its own
fixtures, and know the seams hold.

### Layering rules (where code is allowed to live)

- **`api/` holds routes only** — no business logic. It calls into the pipelines,
  `nlp/`, `rag/`, etc.
- **`scrapers/` is offline and outside `app/`.** The live image ships no Playwright
  or browser binaries. `app/` never imports `scrapers.*`; the reverse (a scraper
  importing `app.*`) is fine. Scrapers run on a laptop or as one-off jobs and write
  to the DB.
- **Prompts are versioned `.j2` files in git** — a prompt change is a PR. Shared
  prompts live in `app/llm/prompts/`; step-specific ones live inside the step dir.

### Coding style — always on

All backend code follows the **`plain-readable-code`** skill (declared in
`CLAUDE.md`): plain language features first, functions that earn their existence,
boring well-maintained libraries over hand-rolled complexity, top-down structure,
comments that explain *why*. This is the default for every task, not opt-in.

---

## Done — by phase

### Phase 0 — Setup + taxonomy cleanup ✅
- Repo scaffolded per design §7 (tooling: uv, ruff, mypy, pytest, pre-commit).
- Minimal FastAPI app (`app/main.py`) — just a `/healthz` endpoint, no DB/routers yet.
- `tests/unit/test_taxonomy_integrity.py` written test-first (integrity assertions).
- `data/taxonomy/categories.json` — 8 categories → `priority_rank`.
- `scripts/build_taxonomy.py` — idempotent `skills_raw.json` → `skills.json`
  (slug ids, ranks, technique entries, alias de-confliction, merges).
- `data/taxonomy/CHANGELOG.md` audit trail.

### Phase 1 + 1.5 — Aliases + matcher ✅ (load-bearing)
- `scripts/generate_aliases.py` — bulk alias generation via `gpt-4o-mini`
  (342 → 1286 aliases). Output in `data/taxonomy/aliases_generated.json`.
- `app/nlp/taxonomy.py` — loads `skills.json` + `categories.json` at boot.
- `app/nlp/matcher.py` — FlashText `KeywordProcessor`, returns canonical skill ids.
  Includes a case-sensitive short-token pass and a `.js` fragment fix (Phase 1.5).
- `app/nlp/audit.py` — drift-detector CLI (`python -m app.nlp.audit`) for
  unmatched skill-shaped tokens.
- `app/nlp/text_clean.py` — text normalization.
- **Eval: F1 = 0.97** on a 19-pair hand-labeled corpus
  (`tests/unit/nlp/test_matcher_eval.py`), plus smoke tests. Fixtures live in
  `tests/fixtures/{resumes,jds}/` and `tests/fixtures/_synthetic/`.
- Two accepted structural limitations documented in
  [`KNOWN_ISSUES.md`](./KNOWN_ISSUES.md) (implied-but-unnamed skills; word-sense
  collisions) — deliberate costs of rule-based extraction, **not bugs to fix**.

### Phase 2 — Course corpus + RAG ✅
- **DB foundation**: `app/db/engine.py` (async SQLAlchemy), `app/models/course.py`
  (`courses`, `course_skills`, `course_embeddings`), first Alembic migration
  `1cea5f98e020_*` with the pgvector extension + HNSW cosine index.
- **Corpus**: DeepLearning.AI only this phase (live site is behind a Cloudflare
  challenge, so we parse saved HTML). `scrapers/deeplearning_ai.py` +
  `scrapers/load_courses.py`. **112 courses**, 231 `course_skills` rows, 57 distinct
  taxonomy ids.
- **Course → skill mapping**: `scripts/map_course_skills.py` (`gpt-4o-mini`,
  precision-tuned, every id validated against the taxonomy).
- **Embeddings**: `scripts/embed_courses.py` → `text-embedding-3-small` (1536-d)
  into `course_embeddings` (all 112 embedded).
- **RAG**: `app/rag/retriever.py` (gap → embed → pgvector cosine top-50) and
  `app/rag/ranker.py` (priority-weighted coverage → Course A / Course B).
- Full write-up: [`backend/docs/phase-2-course-corpus.md`](./backend/docs/phase-2-course-corpus.md).

**Known corpus limitation (documented, accepted):** the corpus is almost entirely
rank-3/rank-4 (GenAI/LLM) skills, so the priority weighting rarely differentiates
and `duration_hours` is NULL for all courses — final A/B tie-breaks fall to
`external_id` (deterministic but not quality-ranked). The ranking *framework* is
correct; adding Coursera/Udemy or a rating signal later makes it fire without a
redesign.

### Phase 3 — Auth + dashboard ✅

Built in three prompts: shared DB foundation, auth, then dashboard.

- **DB foundation** (§6): `app/models/user.py` (`users`) and `app/models/skill.py`
  (`skills`, `skill_aliases`, `user_skills`), Alembic migration
  `b2f4a1c7d3e8_*` chained onto the courses one. `scripts/sync_taxonomy_to_db.py`
  mirrors `skills.json` → Postgres (idempotent upsert; **1078 skills, 1278 aliases**).
- **Auth** (§10 OAuth half, §11): `app/auth/google.py` — Google OIDC via Authlib
  with PKCE; ID-token signature/`aud`/`iss` validation is Authlib's job (JWKS from
  discovery), not hand-rolled. `app/auth/sessions.py` — Redis-backed sessions,
  32-byte opaque id, 7-day **sliding** TTL, no JWTs. `app/db/redis.py` — shared lazy
  client. `app/deps.py` — `get_db`, `get_redis`, `get_current_user`. Routes in
  `app/api/auth.py`: `/auth/google/{login,callback,logout}`, `/me`. Cookie is
  `HttpOnly; Secure(per config); SameSite=Lax`.
- **Dashboard** (F4/F5): `app/api/dashboard.py` — `GET /dashboard` (user_skills
  grouped by category, mock-matching shape) and `PATCH /dashboard` (add/remove
  **manual** skills, unknown id → 422). Every query scoped to the current user.
  `CORSMiddleware` added so the browser can send the session cookie cross-origin.
- **Frontend wired**: `frontend/lib/api/dashboard.ts` + the `(app)/dashboard/` page
  now fetch the live endpoint (identical markup; `tsc` + `next build` clean). The
  signin button still needs to point at `/auth/google/login`.
- **Deps added**: `itsdangerous` (runtime — Starlette `SessionMiddleware`),
  `fakeredis` (dev — session/auth unit tests without live Redis).

**Deferred / noted (status now):**
- **CSRF double-submit token** — ✅ done in Phase 6.
- **PATCH is not wired into the UI yet** — still open; needs a skills-search endpoint +
  picker (the API works; `patchDashboard` is CSRF-ready). GET is fully wired.
- **`last_updated_from` was `null`** — ✅ done in Phase 6 (the F5 merge + `resumes.filename`).
- A live signed-in end-to-end render wasn't exercised in-sandbox — still wants a human
  smoke check; the contract is matched field-for-field and covered by tests.

### Phase 4 — Pipeline 1 (analysis) ✅

Built in five prompts: foundation → steps 1–4 → RAG steps 5–6 → LLM step 7 →
persist + orchestrator + endpoints + plans API/frontend.

- **Foundation**: `resume`/`run`/`plan` models (§6, migration `c3d5e7f9a1b2_*`),
  frozen `PipelineState`, `app/storage/r2.py` (boto3 wrapped in `asyncio.to_thread`,
  bucket-locked, signed URLs), `app/llm/client.py` (async `gpt-4o` chat with tenacity
  retries 1/2/4s + per-call cost from a price table, Logfire-tagged).
- **8 steps** (`app/pipeline_one/0N_*/`), each `run(state) -> state` with
  `logic.py` + `schemas.py` + refreshed README: ingest (size + magic-byte validate,
  sha256, stage to R2), extract_text (pypdf/python-docx → normalize → `.txt`, drop
  binary), extract_skills (shared matcher), gap_analysis (matched/missing/fit,
  priority sort, zero-skill guard), retrieve_courses (embed gap → pgvector top-50),
  select_courses (priority-weighted rank + covered sets + <2 category fallback),
  generate_projects (**two parallel `gpt-4o` calls** via `asyncio.gather`; one fails
  → placeholder, both fail → run fails), persist (immutable `Plan` + complete run).
- **Orchestrator** (`app/pipeline_one/__init__.py`): tiny — ordered step list,
  `importlib` loop, bumps `runs.current_stage`, marks failed on `PipelineStepError`.
  **Arq worker** (`app/workers/{settings,tasks,queue}.py`, `max_tries=1`).
- **API** (`app/api/analyze.py`): `POST /analyze` (multipart, enqueues, 202 +
  `run_id`), `GET /runs/{id}` (poll; maps backend stage 1..8 → the frontend's 6-stage
  `StageList`, `plan_id` when done). **Plans API** (`app/api/plans.py`): `GET /plans`
  (paginated, newest-first), `GET /plans/{id}`, `DELETE /plans/{id}` — all
  user-scoped, 404 (not 403) for non-owners.
- **Frontend wired**: analyze → `POST /analyze`, running → poll `GET /runs/{id}` →
  navigate to the plan, saved → `GET /plans` + row delete, plan page → `GET /plans/{id}`,
  **signin button now points at `/auth/google/login`**. `tsc` + `next build` clean.
- **Deps added**: `moto[s3]` (dev — R2 tests), `[tool.logfire] ignore_no_config`
  (silence "not configured" until Phase 6).
- **e2e test** drives the real Arq task through all 8 steps (OpenAI mocked, moto R2,
  seeded courses): queued → running → completed, `Plan` written with the expected
  gap/courses/projects; plus a failing-step → `failed` test.

**Deferred / noted (not silently skipped):**
- **DTO ⇆ mock reconciliations** (documented in `app/schemas/plans.py`): skills are
  returned as `{id, display_name, category}` objects; **projects are Markdown**
  (`project_*_md`), so the plan page renders Markdown, not the mock's structured
  `ProjectCard`; course display fields are embedded (no courses endpoint).
- **`jd_title` / `jd_company` / `resume_filename` have no backend source** — never
  extracted or persisted; the saved list derives a heading from `jd_text`.
- The Arq job carries `file_bytes` + `jd_text` as args (the raw upload is never
  stored; the JD only lands in the eventual Plan) — see `app/workers/tasks.py`.
- Guest persistence is a Phase-6 `NotImplementedError` in step 8; the orchestrator
  skips run-bookkeeping for guests.
- Live signed-in end-to-end render not exercised in-sandbox (needs real Google OAuth
  + running worker) — verified via `tsc` + `next build` + backend tests; human smoke
  check still wanted.

### Phase 5 — Pipeline 2 (jobs) ✅

Built in three prompts: foundation → 5 steps + cron → `GET /jobs` + frontend.

- **Foundation**: `app/models/job_posting.py` (`job_postings`, `job_skills` with a
  real FK to `skills`), migration `d4e6f8a0b2c3_*`. `app/greenhouse/client.py` — async
  httpx (HTTP/2), **SSRF allowlist** (only slugs in `data/companies.json`; a
  non-allowlisted slug is refused before any request), 500ms spacing, 3-retry backoff,
  per-company skip on failure. `data/companies.json` (25 curated slugs +
  `companies.README.md` on how to verify/extend). Frozen `JobsRefreshState`.
- **5 steps** (`app/pipeline_two/0N_*/`): fetch_boards, filter_recent (≤21 days AND
  US/CA location heuristic), extract_skills (**shared `matcher.py`** on HTML-stripped
  content — `app/common/html.py`, stdlib), upsert (`ON CONFLICT (company, gh_job_id)`,
  replace job_skills), purge_old (`posted_at < now - 21 days`). Tiny orchestrator
  (`app/pipeline_two/__init__.py`).
- **Cron**: `refresh_jobs` task + `WorkerSettings.cron_jobs = [cron(refresh_jobs,
  hour={0,6,12,18})]` — every 6 hours.
- **API** (`app/api/jobs.py`): `GET /jobs` — the §9 ranking (LEFT JOIN job_skills,
  21-day window, overlap = user's skills ∩ job skills, `ORDER BY overlap DESC,
  posted_at DESC`, paginated) with per-job matched/missing skill objects. Postings are
  global; the **ranking is per-user**.
- **Frontend wired**: `frontend/lib/api/jobs.ts` + the `(app)/jobs/` page fetch the
  live endpoint; `JobCard` untouched (page adapts the DTO to its props). `tsc` +
  `next build` clean.
- **Deps added**: `httpx[http2]` (runtime — pulls `h2` for the Greenhouse client's
  HTTP/2). HTML stripping uses stdlib, no new dep.
- **e2e test** runs fetch (mocked) → filter → extract → upsert → purge against the DB;
  plus a two-user ranking-divergence test on `GET /jobs`.

**Deferred / noted (not silently skipped):**
- **`companies.json` slugs are unverified** — curated real companies, but not
  live-checked from the sandbox; a bad slug just 404s and is skipped. Verify/prune with
  the `curl` recipe in `data/companies.README.md` before the cron runs for real.
- **"View posting" button isn't wired to `job.url`** — the mock button was inert too
  and `JobCard` stayed untouched; `url` is in the DTO, ready to wire.
- Job `location` can be null; the page renders `""` for it.

### Phase 6 — Polish + deploy ✅

Built in five prompts: guest flow → rate limits + CSRF → observability → deploy prep →
F5 merge.

- **Guest analysis path** (§10, F3): `POST /analyze` with no cookie → a Redis-only run
  record (`app/guest_runs.py`, 1h TTL), enqueued with `is_guest=True`; the orchestrator
  bumps stage in Redis and step 8 writes the plan payload there — **zero DB rows for
  guests**. `GET /runs/{id}` returns the plan inline; the running page renders it (no
  save/delete, "sign in to save" banner). `get_current_user_optional` added; the authed
  path is byte-for-byte unchanged.
- **Rate limits** (§10/§11, `app/common/rate_limit.py`): a Redis-`INCR` fixed-window
  limiter (reuses the shared client → testable on fakeredis; chosen over slowapi for
  that reason). Guest `/analyze` **5/24h per IP**, authed **20/day per user**, per-IP on
  `/auth/*`. **IPs never stored plaintext** — hashed with a daily-rotating salt. 429 handler
  with a clean JSON body + `Retry-After`.
- **CSRF** (§11, `app/common/csrf.py`): stateless double-submit token (readable cookie
  set at sign-in, echoed in `X-CSRF-Token`) required on `PATCH /dashboard` +
  `DELETE /plans/{id}`; the frontend sends it.
- **Observability** (§12, `app/observability.py`): Logfire (`send_to_logfire=
  "if-token-present"` → no-op without a token; instruments FastAPI/SQLAlchemy/httpx;
  step-boundary spans tagged run_id/user_id/step/latency) + Sentry (Arq + FastAPI,
  disabled without a DSN). **Cost ledger** `llm_calls` (migration `e5f7a9b1c3d4`) written
  per call via `app/llm/cost_ledger.py`, with a Logfire warning when a user tops $0.50/day.
  **Deep healthchecks**: `/healthz` (Postgres+Redis) and `/readyz` (+taxonomy loaded +
  OpenAI authenticates). PII-redaction helpers + Logfire key-scrubbing. Dropped the
  `[tool.logfire]` shim.
- **F5 merge** (F4/F5, §6): step 8 (authed) now writes the `user_skills.source='extracted'`
  partition — `DELETE extracted` then re-insert the resume's skills, **preserving manual
  rows** (re-analysis replaces, never appends). `resumes.filename` added (migration
  `f6a8b0c2d4e6`) so `GET /dashboard`'s `last_updated_from` is real.
- **Deploy config**: `Dockerfile` (uv-based, lean — libmagic only, **no browsers**;
  excludes scrapers/tests/scripts) + `.dockerignore`; `railway.toml` (web: uvicorn,
  `/healthz`, pre-deploy `alembic upgrade head`) + `railway.worker.toml` (arq). Verified:
  **image builds, web + worker both boot** against local Postgres/Redis, migrations run
  in-image. Cross-origin prod cookies: `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`
  (config-driven). Env contract + go-live runbook in
  [`backend/docs/deploy.md`](./backend/docs/deploy.md).
- **Deps added**: `logfire[fastapi,sqlalchemy,httpx]` extras (OTel instrumentations).

**Deferred / noted (not silently skipped):**
- **Human deploy steps remain** — Railway provisioning (Postgres+pgvector, Redis, R2),
  DNS, secret entry, OAuth/CORS at real domains, and first-boot seeding (taxonomy +
  course corpus, run offline from a laptop). All scripted in `docs/deploy.md`.
- **`companies.json` slugs still need live verification** (see below).

---

## Not started — everything downstream

**All 6 phases are code-complete.** Nothing phase-scoped remains. What's left is the
human deploy runbook and the product-polish punch-list below — none of it blocks a
build, and all of it is optional-at-launch except the deploy steps.

- Other course sources (Coursera/Udemy scrapers) — deferred; DeepLearning.AI only.

---

## Gaps / follow-ups to do (the launch punch-list)

Everything deferred across the phases that hasn't been built, gathered so it isn't lost.
The Phase-6 hardening items are all **done** (see the Phase 6 section); these are what's
left before/after a real launch.

### Human deploy steps (from `docs/deploy.md` — not code)
- Provision Railway Postgres+pgvector, Redis, and a Cloudflare R2 bucket.
- Create the two services (web + worker) from the repo; set the full env contract.
- First-boot seeding (one-time, from a laptop against the prod DB, since scripts/scrapers
  aren't in the image): `sync_taxonomy_to_db.py` + the course corpus pipeline.
- Point Google OAuth redirect/origins + `FRONTEND_ORIGIN` at the real domains; set
  `COOKIE_SECURE=true` + `COOKIE_SAMESITE=none`.
- Verify `/healthz` + `/readyz`; run one real signed-in analysis end to end.

### Product gaps (optional at launch)
- **`jd_title` / `jd_company` are not stored** — the saved-plans list derives a heading
  from `jd_text`. Showing a real title/company needs the JD-parse + persist. (Note:
  `resume_filename` is now stored — F5 closed that half.)
- **Dashboard PATCH isn't wired into the UI** — needs a **skills-search endpoint**
  (`GET /skills?q=`) + an id-resolving picker. The API works (`patchDashboard` is
  CSRF-ready); nothing calls it yet.
- **Projects are Markdown, not structured** — step 7 emits Markdown and the plan page
  renders it plainly; a richer view needs a Markdown renderer or a structured schema.
- **Course ranking signal** — corpus is rank-3/4-heavy with NULL `duration_hours`, so
  A/B ties fall to `external_id`. Add ratings/enrollment or durations, and Coursera/Udemy
  for language/framework courses (Phase 2 note).
- **Verify `data/companies.json` slugs** — curated but not live-checked; validate with the
  `curl` recipe in `data/companies.README.md`, prune 404s, grow toward ~200.
- **Wire the jobs "View posting" button** to `job.url` (in the DTO, unused by the UI).
- **Live signed-in smoke test** — the full OAuth → analyze → running → plan → jobs flow
  has only been verified via `tsc`/`next build` + backend tests, never a real browser run.

---

## How to pick up where we left off

```bash
cd backend
docker compose up -d               # Postgres (pgvector) + Redis
uv sync                            # install deps
uv run alembic upgrade head        # all migrations (courses, users/skills, runs/plans, jobs, llm_calls, resumes.filename)
uv run python scripts/sync_taxonomy_to_db.py   # mirror skills.json → Postgres
uv run pytest -q                   # 170 passed with the DB up (0 skipped)

# run the app locally (two processes, same codebase):
uv run uvicorn app.main:app --reload            # the API
uv run arq app.workers.settings.WorkerSettings  # the worker (Pipeline 1 jobs + the 6h jobs cron)

# build the deploy image (both services run from it):
docker build -t skillbridge-backend .
```

To rebuild the course corpus from scratch, follow the offline pipeline in
`backend/docs/phase-2-course-corpus.md`.

**Recommended next action: ship it.** The backend is code-complete; follow
[`backend/docs/deploy.md`](./backend/docs/deploy.md) to provision Railway (Postgres+pgvector,
Redis, R2), set the env contract, seed the taxonomy + course corpus once from a laptop,
point OAuth/CORS at the real domains, and verify `/healthz` + `/readyz`. Then run one real
signed-in analysis end to end (the one flow never exercised in-sandbox). After launch,
work the product-polish punch-list above as needed.
