# Deploy runbook — SkillBridge backend on Railway

Topology (design §5): **two Railway services from one repo + one image** — a `web`
service (FastAPI) and a `worker` service (Arq: Pipeline 1 jobs + the 6-hour jobs cron)
— plus managed **Postgres (pgvector)**, **Redis**, and a **Cloudflare R2** bucket. The
Next.js frontend is on Vercel (a different origin).

Config-as-code lives in `railway.toml` (web) and `railway.worker.toml` (worker); the
image is `Dockerfile`. The steps below (provisioning, secrets, DNS) are **human steps**.

---

## 1. Environment-variable contract

Set these on **both** services (Railway → service → Variables). Reference them from the
shared Postgres/Redis via Railway variable references where possible.

| Variable | Required | Prod value / example | Notes |
|---|---|---|---|
| `APP_ENV` | yes | `production` | Tags Logfire/Sentry env. |
| `DATABASE_URL` | yes | `postgresql+asyncpg://…` | **Must use the `+asyncpg` driver.** Railway's Postgres gives a `postgresql://` URL — prepend `+asyncpg` (or set a reference and edit the scheme). |
| `REDIS_URL` | yes | `redis://…` | Railway Redis. Queue + sessions + guest runs + rate limits. |
| `OPENAI_API_KEY` | yes | `sk-…` | Embeddings + `gpt-4o`. |
| `R2_ACCOUNT_ID` | yes | `<cf-account-id>` | Cloudflare R2. |
| `R2_ACCESS_KEY_ID` | yes | `<key>` | R2 API token. |
| `R2_SECRET_ACCESS_KEY` | yes | `<secret>` | R2 API token. |
| `R2_BUCKET` | yes | `skillbridge-resumes` | Holds extracted resume `.txt` only. |
| `R2_ENDPOINT_URL` | no | *(empty)* | Local-dev override to point storage at MinIO. **Leave empty in prod** — the endpoint is derived from `R2_ACCOUNT_ID`. |
| `GOOGLE_CLIENT_ID` | yes | `<id>.apps.googleusercontent.com` | OAuth. |
| `GOOGLE_CLIENT_SECRET` | yes | `<secret>` | OAuth. |
| `OAUTH_REDIRECT_URI` | yes | `https://api.skillbridge.app/auth/google/callback` | Must be allowlisted in the Google console (step 5). |
| `SESSION_SECRET` | yes | 32+ random bytes | Signs the OAuth-transaction cookie **and** seeds the guest IP daily-salt. Rotating it logs everyone out and rotates the salt. |
| `SESSION_COOKIE_NAME` | no | `sid` | Default is fine. |
| `SESSION_TTL_SECONDS` | no | `604800` | 7-day sliding session. |
| `COOKIE_SECURE` | **yes (prod)** | `true` | HTTPS-only cookies. Required for `COOKIE_SAMESITE=none`. |
| `COOKIE_SAMESITE` | **yes (prod)** | `none` | The Vercel frontend is a different origin, so cross-site `fetch` needs `none` to carry the `sid`/`csrf` cookies. Local http dev uses `lax`. |
| `FRONTEND_ORIGIN` | **yes (prod)** | `https://skillbridge.vercel.app` | The CORS allowlist (credentialed CORS can't use `*`). Exactly the frontend's origin. |
| `SENTRY_DSN` | no | `https://…@sentry.io/…` | Empty → Sentry disabled (safe no-op). |
| `LOGFIRE_TOKEN` | no | `<token>` | Empty → Logfire local no-op (nothing leaves the box). |

There is **no plaintext-secret file** in the repo or image — everything is env-only,
and a pre-commit secret scanner blocks `.env` commits. `.env.example` mirrors this list.

**Frontend (Vercel):** set `NEXT_PUBLIC_API_URL=https://api.skillbridge.app` so the SPA
calls the API. It must equal `OAUTH_REDIRECT_URI`'s host and be listed in
`FRONTEND_ORIGIN` on the backend.

---

## 2. Provision the managed services

1. **Postgres + pgvector** — add Railway's Postgres plugin. Enable pgvector: the first
   migration runs `CREATE EXTENSION IF NOT EXISTS vector`, so no manual step is needed
   as long as the image/version supports it (Railway's Postgres does). Copy its
   connection URL into `DATABASE_URL` (switch the scheme to `postgresql+asyncpg://`).
2. **Redis** — add Railway's Redis plugin; copy its URL into `REDIS_URL`.
3. **Cloudflare R2** — create a bucket (`skillbridge-resumes`) and an API token scoped
   to that bucket; fill the four `R2_*` vars. Egress is free; the bucket holds only the
   extracted resume `.txt` files.

---

## 3. Create the two Railway services

Both point at this repo with **root directory = `backend/`** and build the `Dockerfile`.

- **web** — uses `railway.toml`: start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
  healthcheck `/healthz`, and a **pre-deploy hook `alembic upgrade head`** (migrations
  run here, once per deploy).
- **worker** — set its config path to `railway.worker.toml`: start
  `arq app.workers.settings.WorkerSettings`. No healthcheck, no pre-deploy (it does not
  repeat migrations).

Set the env-var contract (section 1) on both services.

---

## 4. First-boot seeding (one-time, from a laptop)

Migrations run automatically (the web service's pre-deploy hook). Seeding the
**taxonomy** and the **course corpus** is a one-time step run from a laptop clone
against the prod DB — the scrapers and seed scripts are offline-only and are **not in
the image** (§7). With the prod `DATABASE_URL` (async) exported locally:

```bash
cd backend
export DATABASE_URL='postgresql+asyncpg://…prod…'
export OPENAI_API_KEY='sk-…'         # needed for the course embed step

uv run python scripts/sync_taxonomy_to_db.py     # skills.json → skills + skill_aliases
# Course corpus (see backend/docs/phase-2-course-corpus.md for the full pipeline):
uv run python scrapers/deeplearning_ai.py        # parse saved HTML → JSON
uv run python scrapers/load_courses.py           # JSON → courses
uv run python scripts/map_course_skills.py       # courses → course_skills (LLM, validated)
uv run python scripts/embed_courses.py           # courses → course_embeddings
```

All seeders are idempotent, so re-running is safe.

---

## 5. Point OAuth + CORS at the real domains

1. **Google Cloud console** (OAuth client): add the authorized redirect URI
   `https://api.skillbridge.app/auth/google/callback` and the authorized JavaScript
   origin `https://skillbridge.vercel.app`. Set `OAUTH_REDIRECT_URI` to match.
2. **CORS**: set `FRONTEND_ORIGIN` to the exact Vercel origin.
3. **Cookies**: `COOKIE_SECURE=true` + `COOKIE_SAMESITE=none` so the cross-origin SPA
   can carry the `sid`/`csrf` cookies. (Cross-site CSRF is still covered by the
   double-submit token; SameSite is no longer the only guard.)

---

## 6. Verify

- `GET https://api.skillbridge.app/healthz` → **200** `{"status":"ok",…}` (Postgres +
  Redis reachable). Railway's healthcheck also polls this.
- `GET https://api.skillbridge.app/readyz` → **200** `{"status":"ready",…}` (adds
  taxonomy-loaded + OpenAI-authenticates). If `readyz` is 503 but `healthz` is 200,
  check `OPENAI_API_KEY` and that seeding (section 4) ran.
- Sign in end-to-end from the Vercel app: Google → callback → `/analyze` → a completed
  plan. Confirm the `sid` cookie is set with `Secure; SameSite=None`.

---

## 7. Go-live checklist

- [ ] Postgres, Redis, R2 provisioned; env contract set on **both** services.
- [ ] `DATABASE_URL` uses `postgresql+asyncpg://`.
- [ ] Web deploy ran `alembic upgrade head` (check the deploy logs); `alembic current`
      is at head.
- [ ] Taxonomy synced (`skills` populated) and course corpus seeded (`courses` /
      `course_embeddings` populated).
- [ ] Google OAuth redirect URI + JS origin allowlisted; `OAUTH_REDIRECT_URI` matches.
- [ ] `FRONTEND_ORIGIN` = the Vercel origin; `COOKIE_SECURE=true`; `COOKIE_SAMESITE=none`.
- [ ] `/healthz` and `/readyz` both 200.
- [ ] One real signed-in analysis produces a saved plan; `/jobs` returns ranked jobs
      after the first cron run (or trigger `refresh_jobs` once).
- [ ] Sentry receiving events and Logfire receiving spans (if their tokens are set).

---

## Rollback

Railway keeps every build — one-click redeploy of a previous release. Migrations follow
expand → migrate → contract (design §13), so a previous image stays compatible with the
current schema for the common case.
