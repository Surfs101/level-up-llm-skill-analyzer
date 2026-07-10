# SkillBridge Backend

A FastAPI service on Railway with one async Arq worker, one Postgres (with
`pgvector`), one Redis, and one R2 bucket — wrapping two cleanly separated
pipelines: **Analysis** (resume + JD → skill diff → RAG-retrieved courses →
priority-weighted top-2 selection → two LLM-generated portfolio projects → saved
plan) and **Jobs** (Greenhouse boards refreshed every 6 hours, ranked per-user
by skill overlap). Every skill enters through one canonical-skill matcher backed
by a single source of truth, `data/taxonomy/skills.json`.

See [`../skillbridge-backend-design.md`](../skillbridge-backend-design.md) for
the full system design.

## Quickstart

```bash
uv sync                                    # install dependencies into .venv
cp .env.example .env                       # fill in real values
docker compose up -d                       # start Postgres + Redis locally
uv run uvicorn app.main:app --reload       # serve the API at http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/healthz         # -> {"status":"ok"}
```

Run the worker (Pipeline 1 jobs + the 6-hour jobs cron) alongside the API:

```bash
uv run arq app.workers.settings.WorkerSettings
```

## Development

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy app/                                       # type-check the app package
uv run pytest                                          # run tests
```

## Deployment

Two Railway services (`web` + `worker`) from one `Dockerfile`, plus Postgres/Redis/R2.
The full env-var contract and the go-live runbook are in
[`docs/deploy.md`](docs/deploy.md); `railway.toml` (web) and `railway.worker.toml`
(worker) hold the config-as-code.
