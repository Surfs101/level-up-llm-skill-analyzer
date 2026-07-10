"""Embed the course corpus once into course_embeddings.

Seed/build script (offline). For every course it builds `title + description`,
embeds it via app.llm.embeddings (text-embedding-3-small), and upserts the vector.
EVERY course is embedded — including the ones with no mapped skills: an empty skill
set doesn't mean empty text, and those courses must still be retrievable.

This is EMBED ONCE — there is no refresh cron. Default embeds only courses that
lack a vector; --refresh re-embeds everything.

    uv run python scripts/embed_courses.py
    uv run python scripts/embed_courses.py --refresh
"""

import argparse
import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.engine import get_sessionmaker  # noqa: E402
from app.llm.embeddings import embed_texts  # noqa: E402
from app.models import Course, CourseEmbedding  # noqa: E402

# OpenAI accepts thousands of inputs per request; 100 keeps each call modest.
BATCH_SIZE = 100


def main() -> None:
    asyncio.run(run(parse_args()))


async def run(args: argparse.Namespace) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        courses = await load_courses_to_embed(session, args)
        print(f"{len(courses)} course(s) to embed (refresh={args.refresh}).")
        if not courses:
            return

        embedded = 0
        for batch in chunked(courses, BATCH_SIZE):
            vectors = await embed_texts([course_text(course) for course in batch])
            for course, vector in zip(batch, vectors, strict=True):
                await upsert_embedding(session, course.id, vector)
            await session.commit()  # persist each batch so a crash doesn't lose progress
            embedded += len(batch)
            print(f"  embedded {embedded}/{len(courses)}")

    print(f"done: {embedded} course(s) embedded.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed courses into course_embeddings.")
    parser.add_argument(
        "--refresh", action="store_true", help="Re-embed all courses, not just the missing ones."
    )
    parser.add_argument("--limit", type=int, default=None, help="Embed only the first N courses.")
    return parser.parse_args()


async def load_courses_to_embed(session, args: argparse.Namespace) -> list[Course]:  # type: ignore[no-untyped-def]
    """Courses needing a vector: all of them with --refresh, else those lacking one."""
    statement = select(Course)
    if not args.refresh:
        has_embedding = exists().where(CourseEmbedding.course_id == Course.id)
        statement = statement.where(~has_embedding)
    statement = statement.order_by(Course.title)
    if args.limit is not None:
        statement = statement.limit(args.limit)
    return list((await session.scalars(statement)).all())


def course_text(course: Course) -> str:
    """The text we embed: title plus description (description may be empty)."""
    return f"{course.title}\n\n{course.description or ''}".strip()


async def upsert_embedding(session, course_id, vector: list[float]) -> None:  # type: ignore[no-untyped-def]
    statement = pg_insert(CourseEmbedding).values(course_id=course_id, embedding=vector)
    statement = statement.on_conflict_do_update(
        index_elements=["course_id"],
        set_={"embedding": statement.excluded.embedding, "embedded_at": func.now()},
    )
    await session.execute(statement)


def chunked(items: list[Course], size: int) -> Iterator[list[Course]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


if __name__ == "__main__":
    main()
