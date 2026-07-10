"""Mirror the canonical taxonomy (data/taxonomy/skills.json) into Postgres.

Seed/build script (offline). Loads every skill through the taxonomy loader — which
validates as it reads — and upserts them into the `skills` and `skill_aliases`
tables so the rest of the system can join against them.

Idempotent: it upserts on the primary key (skill id, alias), so re-running with the
same skills.json changes nothing and never accumulates duplicate rows.

    uv run python scripts/sync_taxonomy_to_db.py

Upsert-only by design: it does not delete rows absent from the file. That keeps it
from ever removing a `skills` row a `user_skills` row still references. When the
taxonomy actually drops a skill, prune it in a dedicated migration, not here.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.engine import get_sessionmaker  # noqa: E402
from app.models import Skill, SkillAlias  # noqa: E402
from app.nlp.taxonomy import get_all_skills  # noqa: E402


def main() -> None:
    asyncio.run(run())


async def run() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        skill_count, alias_count = await sync(session)
        await session.commit()
        db_skills = await session.scalar(select(func.count()).select_from(Skill))
        db_aliases = await session.scalar(select(func.count()).select_from(SkillAlias))

    print(f"synced {skill_count} skills, {alias_count} aliases from skills.json")
    print(f"table row counts now: skills={db_skills}, skill_aliases={db_aliases}")


async def sync(session) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    """Upsert every skill + alias into the DB. Returns (skill count, alias count).

    Does not commit — the caller owns the transaction, so tests can roll back.
    """
    skills = get_all_skills()
    skill_rows = [
        {
            "id": skill.id,
            "display_name": skill.canonical_name,
            "category": skill.category,
            "priority_rank": skill.priority_rank,
        }
        for skill in skills
    ]
    alias_rows = [
        {"alias": alias, "skill_id": skill.id} for skill in skills for alias in skill.aliases
    ]

    await upsert_skills(session, skill_rows)
    await upsert_aliases(session, alias_rows)
    return len(skill_rows), len(alias_rows)


async def upsert_skills(session, rows: list[dict]) -> None:  # type: ignore[no-untyped-def]
    statement = pg_insert(Skill).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "display_name": statement.excluded.display_name,
            "category": statement.excluded.category,
            "priority_rank": statement.excluded.priority_rank,
        },
    )
    await session.execute(statement)


async def upsert_aliases(session, rows: list[dict]) -> None:  # type: ignore[no-untyped-def]
    statement = pg_insert(SkillAlias).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=["alias"],
        set_={"skill_id": statement.excluded.skill_id},
    )
    await session.execute(statement)


if __name__ == "__main__":
    main()
