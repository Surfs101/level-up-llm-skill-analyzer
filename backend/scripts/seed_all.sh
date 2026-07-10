#!/usr/bin/env bash
# One-shot database seeding — runs the five seed steps in the required order.
#
# Use it once after migrations, both for local dev and for the prod first-boot
# seeding in docs/deploy.md §4. All seeders are idempotent, so re-running is safe.
#
# Needs DATABASE_URL (async driver) and OPENAI_API_KEY in the environment — locally
# these come from backend/.env; against prod, export the prod values first:
#
#   export DATABASE_URL='postgresql+asyncpg://…prod…'
#   export OPENAI_API_KEY='sk-…'
#   ./scripts/seed_all.sh
#
# The last two steps call OpenAI and cost money.

set -euo pipefail
cd "$(dirname "$0")/.."   # run from backend/

echo "1/5  taxonomy  → skills + skill_aliases"
uv run python scripts/sync_taxonomy_to_db.py

echo "2/5  scrape    → parse saved course HTML to JSON (offline)"
uv run python scrapers/deeplearning_ai.py

echo "3/5  courses   → load course JSON into the DB"
uv run python scrapers/load_courses.py

echo "4/5  map       → course_skills (LLM, spends OpenAI credits)"
uv run python scripts/map_course_skills.py

echo "5/5  embed     → course_embeddings (spends OpenAI credits)"
uv run python scripts/embed_courses.py

echo "Done. Course corpus and taxonomy are seeded."
