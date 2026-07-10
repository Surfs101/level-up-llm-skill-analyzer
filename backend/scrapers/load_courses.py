"""Load parsed DeepLearning.AI courses into the `courses` table.

OFFLINE tooling. Reads scrapers/output/deeplearning_ai_courses.json and upserts
each course on (platform, external_id) using the app's async engine.

Import direction note: the app must never import scrapers.*, but the reverse is
fine and intended — offline jobs reach the same database through the app's models
and engine. Run after the parser, with Postgres up:

    uv run python scrapers/load_courses.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Run directly as `python scrapers/load_courses.py`, which puts scrapers/ (not the
# backend root) on sys.path — so add the backend root to reach the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.db.engine import get_sessionmaker  # noqa: E402
from app.models import Course  # noqa: E402

PLATFORM = "deeplearning_ai"
SCRAPERS_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRAPERS_DIR / "output" / "deeplearning_ai_courses.json"


async def load_courses(input_path: Path) -> int:
    """Upsert every course row from the JSON file; return how many were processed."""
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for row in rows:
            await session.execute(_upsert_statement(row))
        await session.commit()
    return len(rows)


def _upsert_statement(row: dict):  # type: ignore[no-untyped-def]
    """INSERT … ON CONFLICT (platform, external_id) DO UPDATE for one course row."""
    statement = pg_insert(Course).values(
        platform=PLATFORM,
        external_id=row["external_id"],
        title=row["title"],
        description=row.get("description"),
        url=row["url"],
        level=row.get("level"),
        duration_hours=row.get("duration_hours"),
    )
    return statement.on_conflict_do_update(
        index_elements=["platform", "external_id"],
        set_={
            "title": statement.excluded.title,
            "description": statement.excluded.description,
            "url": statement.excluded.url,
            "level": statement.excluded.level,
            "duration_hours": statement.excluded.duration_hours,
            "scraped_at": func.now(),  # re-scraped: refresh the timestamp
        },
    )


def main() -> None:
    count = asyncio.run(load_courses(DEFAULT_INPUT))
    print(f"upserted {count} courses into platform={PLATFORM!r}")


if __name__ == "__main__":
    main()
