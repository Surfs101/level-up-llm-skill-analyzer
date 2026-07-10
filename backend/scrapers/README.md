# Scrapers — offline tooling

Offline tooling. **Never imported by `app/`.** The reverse is fine and intended:
these scripts import `app.models` / `app.db` to reach the same database. Runs on a
laptop or as a one-off job; the live FastAPI/worker image ships none of this.

Raw data is gitignored (`input/`, `output/`, `.cache/`); only the code is committed.

## DeepLearning.AI (saved-HTML parser, no network)

The site is behind a Cloudflare managed challenge that only clears for a real human
on a residential IP, so we don't fetch it live. A human saves the fully-rendered
course listing page into `input/`, then:

```bash
# 1. Parse saved HTML -> structured JSON
uv run python scrapers/deeplearning_ai.py
#    reads input/*.html, writes output/deeplearning_ai_courses.json

# 2. Load JSON -> courses table (needs Postgres up: docker compose up -d)
uv run python scrapers/load_courses.py
#    upserts on (platform='deeplearning_ai', external_id)
```

`deeplearning_ai.py` reconstructs the Next.js App Router `__next_f` streamed payload
and extracts each course (title, description, url, level; duration isn't in the
listing, so it stays null).
