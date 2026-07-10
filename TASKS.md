# SkillBridge 2.0 — Bring-Up Tasks

The code is essentially complete. What's left is **runtime setup + real credentials**, not features.
This splits the work into what **only you can do** (accounts, secrets, spending money) and what **I can do for you**.

---

## 🧑 You have to do these (accounts / secrets / money)

| # | Task | Why it's yours |
|---|------|----------------|
| 1 | ~~**Provide Cloudflare R2 credentials** — *or* use local MinIO~~ | ✅ **Resolved for local dev** — using MinIO (task A). Only needed again for a **prod** deploy (fill the four `R2_*` vars from a real Cloudflare bucket). |
| 2 | **Confirm/rotate the OpenAI API key** in `backend/.env` | A live-looking key is sitting in your working tree — rotate it, then confirm the valid one. Seeding + analysis spend OpenAI credits. |
| 3 | **Create Google OAuth credentials** (only for sign-in / saved plans) | Google Cloud Console → OAuth client (Web), redirect URI `http://localhost:8000/auth/google/callback`. Guest analysis works without this. |
| 4 | **Approve spending** on the two seed steps (`map_course_skills`, `embed_courses`) | They call OpenAI and cost money. Say go and I run them. |

---

## 🤖 I can do these for you

| # | Task | Status |
|---|------|--------|
| C | **Manual jobs-trigger script** | ✅ Done — `backend/scripts/trigger_jobs.py` (enqueues `refresh_jobs` once). |
| D | **Fix env var name mismatch** | ✅ Done — `.env` now uses `OAUTH_REDIRECT_URI`. |
| F | **Seed-all script** | ✅ Done — `backend/scripts/seed_all.sh` runs all 5 seed steps in order (local **and** prod §4). |
| A | **Set up local MinIO** as a free R2 substitute | ✅ Done — docker-compose starts MinIO + auto-creates the `skillbridge-resumes` bucket; `.env` points at it via `R2_ENDPOINT_URL`. Verified put/get/signed-URL/delete end-to-end. Local-dev only; prod still uses R2 (leave `R2_ENDPOINT_URL` empty). |
| B | **Bring-up script** (`dev.sh`) | ✅ Done — `backend/scripts/dev.sh`: docker up (Postgres/Redis/MinIO) → `alembic upgrade head` → starts API + worker + frontend, waits for `/healthz`, Ctrl-C stops them. `--no-serve` does infra+migrate only. Does **not** seed (paid steps stay opt-in). |
| E | **Run migrate + bring-up end-to-end** | ✅ Done — ran `dev.sh`; migrations at head (`f6a8b0c2d4e6`), full stack verified: `/healthz` + `/readyz` both 200 (`taxonomy:true`, `openai:true`), worker connected, frontend serving on :3000. DB volume already holds a full seed (skills=1078, courses=112, embeddings=112), so **no paid seed steps were run**. |

---

## 📝 How to fill `backend/.env`

Edit `backend/.env`. Leave anything marked ✅ as-is.

| Variable | What to put | How to get it |
|----------|-------------|---------------|
| `DATABASE_URL` | ✅ keep default | Matches docker-compose Postgres. Don't change for local. |
| `REDIS_URL` | ✅ keep default | Matches docker-compose Redis. Don't change for local. |
| `OPENAI_API_KEY` | your real key `sk-proj-...` | platform.openai.com → API keys → **rotate** the current one and paste the new value. |
| `R2_ENDPOINT_URL` | ✅ `http://localhost:9000` | Local MinIO. Leave empty in prod (endpoint derived from `R2_ACCOUNT_ID`). |
| `R2_ACCOUNT_ID` | ✅ `minio` (local) | Prod: Cloudflare dash → R2 → account ID (top right). |
| `R2_ACCESS_KEY_ID` | ✅ `minioadmin` (local) | Prod: Cloudflare → R2 → **Manage API Tokens** → create token. |
| `R2_SECRET_ACCESS_KEY` | ✅ `minioadmin` (local) | Prod: shown once when you create the token above. |
| `R2_BUCKET` | ✅ `skillbridge-resumes` | Auto-created in MinIO by docker-compose. Prod: create in R2. |
| `GOOGLE_CLIENT_ID` | OAuth client ID | Google Cloud Console → APIs & Services → Credentials → **OAuth client ID (Web)**. Only needed for sign-in. |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | Same screen as above. |
| `OAUTH_REDIRECT_URI` | ✅ already fixed | Was misnamed `GOOGLE_REDIRECT_URI`; I renamed it. Value stays `http://localhost:8000/auth/google/callback`. |
| `SESSION_SECRET` | 32+ random chars | Run `openssl rand -hex 32` and paste the output. |

**Vars not in your `.env` but supported (optional — safe to skip locally):**
`COOKIE_SECURE=false`, `COOKIE_SAMESITE=lax`, `FRONTEND_ORIGIN=http://localhost:3000`,
`SENTRY_DSN=` (empty), `LOGFIRE_TOKEN=` (empty). Defaults are fine; add only if needed.

**Bare minimum to run guest analysis** (no sign-in): valid `OPENAI_API_KEY` + working R2/MinIO. Everything else can wait.

---

## Order of operations
1. ✅ Me: env fix, jobs-trigger script, seed-all script → C, D, F (done)
2. ✅ Me: local MinIO as the R2 substitute → task 1 / A (done)
3. ✅ Me: local bring-up script (`dev.sh`) → B (done).
4. ✅ Me: migrate + full local bring-up, verified end-to-end → E (done; no paid steps run).
5. ⏳ **You: actually rotate the OpenAI key → task 2** (see warning below — it authenticates but is the same exposed key).
6. You (optional): Google OAuth for sign-in → task 3 (skipped for now, per your call).

**Leftovers, in short:** the stack runs locally today. The only real to-do is **task 2 — genuinely rotate the OpenAI key** (it works but is the previously-exposed one). Paid re-seeding isn't needed — the corpus is already in the DB. Google OAuth (task 3) stays optional.

> ⚠️ **Security — the OpenAI key was NOT rotated.** The key now in `backend/.env` is byte-identical to the one that was already exposed in the tree, and a copy was pasted into the **git-tracked** `backend/.env.example` (which will leak on push). Treat it as compromised: create a new key at platform.openai.com, put it in `backend/.env` only, and remove the real value from `.env.example`. (I left both files untouched pending your go-ahead.)

---

## Minimum path to a working local run (reference)
```bash
cd backend && docker compose up -d           # Postgres + Redis + MinIO (bucket auto-created)
# storage is already set to MinIO in backend/.env — just add your OPENAI_API_KEY
uv run alembic upgrade head
./scripts/seed_all.sh                         # all 5 seed steps (last 2 spend OpenAI $)
uv run uvicorn app.main:app --reload          # terminal 1
uv run arq app.workers.settings.WorkerSettings   # terminal 2
cd frontend && npm run dev                    # terminal 3
# optional: uv run python scripts/trigger_jobs.py   # fill /jobs now instead of waiting 6h
```

---

## 🚂 Railway deployment — how easy is it?

**Backend: very easy — it's already wired for Railway.** The repo ships config-as-code:
- `backend/railway.toml` → **web** service (uvicorn, `/healthz` healthcheck, auto-runs `alembic upgrade head` on every deploy).
- `backend/railway.worker.toml` → **worker** service (arq: Pipeline-1 jobs + the 6h jobs cron).
- `backend/Dockerfile` builds both. Full runbook in `backend/docs/deploy.md`.

**Frontend: designed for Vercel** (zero-config — Vercel auto-detects Next.js). It can also run on Railway (Nixpacks builds Next.js with no config), your choice.

### If you complete the setup tasks, deploy is basically: provision → set env vars → seed once.

**You do (Railway can't do these for you):**
1. **Create a Railway project**, add **Postgres (pgvector)** + **Redis** plugins.
2. **Create 2 services** from this repo, root dir = `backend/`:
   - `web` (uses `railway.toml`), `worker` (set config path to `railway.worker.toml`).
3. **Set env vars on BOTH services** (see `deploy.md` §1). Prod differences from local:
   - `APP_ENV=production`, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`
   - `DATABASE_URL` must keep the **`+asyncpg`** driver (Railway gives plain `postgresql://` — prepend it)
   - `FRONTEND_ORIGIN` = your Vercel/Railway frontend URL
   - `OAUTH_REDIRECT_URI` = `https://<your-api-domain>/auth/google/callback`
4. **Seed once from your laptop** against the prod DB (scrapers aren't in the image, by design):
   ```bash
   export DATABASE_URL='postgresql+asyncpg://…prod…'
   export OPENAI_API_KEY='sk-…'
   cd backend && ./scripts/seed_all.sh
   ```
5. **Deploy the frontend** (Vercel: import repo, set `NEXT_PUBLIC_API_URL=https://<your-api-domain>`).
6. **Google OAuth**: add the prod redirect URI + JS origin in Google Cloud console.
7. Verify `/healthz` and `/readyz` are both 200; run `trigger_jobs.py` (or wait for the cron) to fill `/jobs`.

**Verdict:** Yes — after you finish the local setup tasks, Railway deploy is straightforward. The only genuinely manual bits are provisioning the plugins, pasting env vars, and the one-time laptop seed. No code changes required.
