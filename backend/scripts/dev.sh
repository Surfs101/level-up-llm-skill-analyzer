#!/usr/bin/env bash
# Local dev bring-up. One command to go from nothing to a running stack:
#
#   1. docker compose up   → Postgres + Redis + MinIO (bucket auto-created)
#   2. alembic upgrade      → schema to head
#   3. start                → FastAPI (uvicorn), the Arq worker, and the Next.js frontend
#
# Ctrl-C stops everything it started (the docker services keep running — stop them with
# `docker compose down`). Seeding is intentionally NOT run here: two of the five seed
# steps spend OpenAI credits. Seed separately with `scripts/seed_all.sh` once you're
# ready (see the note this script prints if the DB looks empty).
#
# Usage:
#   scripts/dev.sh              # infra + migrate + serve (API, worker, frontend)
#   scripts/dev.sh --no-serve   # infra + migrate only, then exit (no long-running procs)

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
backend_dir=$(cd "$script_dir/.." && pwd)
repo_dir=$(cd "$backend_dir/.." && pwd)
frontend_dir="$repo_dir/frontend"
log_dir="$backend_dir/.dev-logs"

serve=true
[ "${1:-}" = "--no-serve" ] && serve=false

cd "$backend_dir"

# --- 1. Infrastructure --------------------------------------------------------

echo "==> Starting Postgres + Redis (waiting for healthy)…"
docker compose up -d --wait db redis

echo "==> Starting MinIO (bucket auto-created by the minio-setup container)…"
docker compose up -d minio minio-setup

# The app talks to MinIO over the S3 port; make sure it's accepting connections
# before we hand control to the services. The bucket itself is created by the
# one-shot minio-setup container (idempotent).
echo -n "==> Waiting for MinIO on localhost:9000 "
for _ in $(seq 1 30); do
  if (exec 3<>/dev/tcp/localhost/9000) 2>/dev/null; then
    exec 3>&- 3<&-
    echo "— ready."
    break
  fi
  echo -n "."
  sleep 1
done

# --- 2. Migrations ------------------------------------------------------------

echo "==> Applying database migrations (alembic upgrade head)…"
uv run alembic upgrade head

# --- 3. Seeding reminder (never auto-run — the paid steps cost money) ----------

skill_count=$(docker compose exec -T db \
  psql -U skillbridge -d skillbridge -tAc "SELECT count(*) FROM skills" 2>/dev/null || echo 0)
if [ "${skill_count//[!0-9]/}" = "0" ]; then
  echo
  echo "  NOTE: the database has no skills yet — it isn't seeded."
  echo "        Guest analysis needs the taxonomy + course corpus. Seed it with:"
  echo "            scripts/seed_all.sh"
  echo "        Heads-up: the last two seed steps call OpenAI and cost money."
  echo
fi

if [ "$serve" = false ]; then
  echo "==> Infra + migrations done (--no-serve). Docker services are still running."
  exit 0
fi

# --- 4. Application processes --------------------------------------------------

mkdir -p "$log_dir"
pids=()

# Each service runs in its own session (setsid) so we can stop it and all of its
# children as a process group on the way out.
start() {
  local name="$1"; shift
  setsid bash -c "$1" >"$log_dir/$name.log" 2>&1 &
  pids+=("$!")
  echo "    $name → pid $! (logs: backend/.dev-logs/$name.log)"
}

cleanup() {
  echo
  echo "==> Stopping dev services…"
  for pid in "${pids[@]}"; do
    kill -TERM -- -"$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "    Done. Docker services are still up (stop them with: docker compose down)."
}
trap cleanup EXIT INT TERM

echo "==> Starting app services…"
start api      "cd '$backend_dir' && exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start worker   "cd '$backend_dir' && exec uv run arq app.workers.settings.WorkerSettings"
start frontend "cd '$frontend_dir' && exec npm run dev"

# Wait for the API to answer liveness before declaring the stack up.
echo -n "==> Waiting for the API on http://localhost:8000/healthz "
for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "— healthy."
    break
  fi
  echo -n "."
  sleep 1
done

echo
echo "  SkillBridge is up:"
echo "    Frontend  →  http://localhost:3000"
echo "    API       →  http://localhost:8000  (/healthz, /readyz, /docs)"
echo "    MinIO UI  →  http://localhost:9001  (minioadmin / minioadmin)"
echo
echo "  Tailing logs. Press Ctrl-C to stop the app services."
echo
# Block on the app processes; Ctrl-C triggers cleanup() via the trap.
wait
