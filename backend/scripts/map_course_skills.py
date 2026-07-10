"""Map each course to the canonical taxonomy skill ids it genuinely teaches.

Seed/build script (offline). Reads courses from the DB, asks gpt-4o-mini which
skills each course *teaches* (precision over recall), validates every returned id
against the taxonomy, and writes course_skills.

course_skills only ever holds canonical taxonomy slugs — the same ids the matcher
produces — so course retrieval and gap analysis score against the same vocabulary.

    uv run python scripts/map_course_skills.py --dry-run --limit 10
    uv run python scripts/map_course_skills.py            # full run

PRECISION is the whole point: a falsely-claimed skill makes a course win
gap-coverage it shouldn't and misdirects the recommendation. The prompt forbids
"mentioned in passing" skills, temperature is 0, and unknown ids are dropped.
"""

import argparse
import asyncio
import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from sqlalchemy import delete, exists, or_, select
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db.engine import get_sessionmaker  # noqa: E402
from app.models import Course, CourseSkill  # noqa: E402
from app.nlp.taxonomy import get_all_skills, get_surface_to_id_map  # noqa: E402

# The model sometimes echoes the allowed-list format "id (Canonical Name)"; strip
# the trailing parenthetical so the bare id validates.
_PAREN_SUFFIX = re.compile(r"\s*\(.*\)\s*$")

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT_TEMPLATE = """\
You are mapping a course to the technical skills it SUBSTANTIALLY TEACHES.
Return what the course is fundamentally about — the skills a syllabus or "what
you'll learn" would list, INCLUDING its core subject and domain even when the title
frames that subject as an application. For example: a retrieval course teaches
retrieval/RAG and vector search; an image-generation course teaches generative AI
and computer vision; a course on building X with framework Y teaches both X's
domain and Y. EXCLUDE only skills that are incidental — mentioned in passing, listed
as prerequisites, or tangential examples the course does not actually train. A
genuinely non-technical overview course may map to nothing. Precision still matters
(a wrong skill is worse than a missing one), but the subject the course is ABOUT
must be included, not dropped as "just an application".
Choose ONLY from the allowed list below. Each line is `id (Canonical Name)`. Return
ONLY the id — the exact slug before the parenthesis. Example: from `fastapi (FastAPI)`
return `fastapi`, never `fastapi (FastAPI)` and never `FastAPI`.
{allowed}
Return STRICT JSON: {{"skill_ids": ["<id>", ...]}}  (empty list if unclear)."""


@dataclass
class CourseRow:
    id: uuid.UUID
    external_id: str
    title: str
    description: str | None


@dataclass
class Mapping:
    course: CourseRow
    accepted: list[str]
    dropped: list[str]  # ids the model returned that aren't real taxonomy ids


def main() -> None:
    asyncio.run(run(parse_args()))


async def run(args: argparse.Namespace) -> None:
    valid_ids = {skill.id for skill in get_all_skills()}
    surface_map = get_surface_to_id_map()  # alias/canonical surface -> id, like the matcher
    system_prompt = build_system_prompt()
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        courses = await load_courses(session, args)
        print(f"{len(courses)} course(s) to map (model={MODEL}, dry_run={args.dry_run}).")

        mappings: list[Mapping] = []
        for index, course in enumerate(courses, start=1):
            proposed = await map_course(client, system_prompt, course)
            accepted, dropped = resolve_ids(proposed, valid_ids, surface_map)
            mappings.append(Mapping(course, accepted, dropped))
            print(
                f"  [{index}/{len(courses)}] {course.external_id}: {accepted}"
                + (f"  DROPPED {dropped}" if dropped else "")
            )
            if not args.dry_run:
                await replace_course_skills(session, course.id, accepted)
                await session.commit()  # persist per course so progress survives a crash

    report(mappings, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map courses to taxonomy skill ids via gpt-4o-mini."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Call the LLM and report; write nothing."
    )
    parser.add_argument("--limit", type=int, default=None, help="Map only the first N courses.")
    parser.add_argument(
        "--course-id",
        default=None,
        help="Map only these courses (one or more comma-separated UUIDs or "
        "external_ids), re-mapping even if already done. Useful for dry-run samples.",
    )
    return parser.parse_args()


def build_system_prompt() -> str:
    """The instructions plus the full allowed id list (stable across calls)."""
    allowed = "\n".join(f"{skill.id} ({skill.canonical_name})" for skill in get_all_skills())
    return SYSTEM_PROMPT_TEMPLATE.format(allowed=allowed)


def resolve_ids(
    proposed: list[str], valid_ids: set[str], surface_map: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Turn the model's raw tokens into validated canonical ids.

    Each token is normalized (a trailing "(Canonical)" stripped, lowercased), then
    accepted if it is a real id, or resolved through the matcher's surface map if it
    is a known alias/canonical name (e.g. "llms" -> "large-language-models").
    Anything else is a hallucination: dropped and returned for logging.
    """
    accepted: list[str] = []
    dropped: list[str] = []
    for token in proposed:
        normalized = _PAREN_SUFFIX.sub("", token).strip().lower()
        skill_id = normalized if normalized in valid_ids else surface_map.get(normalized)
        if skill_id is None:
            dropped.append(token)
        elif skill_id not in accepted:
            accepted.append(skill_id)
    return accepted, dropped


async def load_courses(session, args: argparse.Namespace) -> list[CourseRow]:  # type: ignore[no-untyped-def]
    """Courses to map: a single targeted course, or all that lack course_skills rows."""
    statement = select(Course)
    if args.course_id:
        values = [v.strip() for v in args.course_id.split(",") if v.strip()]
        statement = statement.where(or_(*[_course_id_filter(v) for v in values]))
    else:
        already_mapped = exists().where(CourseSkill.course_id == Course.id)
        statement = statement.where(~already_mapped)
    statement = statement.order_by(Course.title)
    if args.limit is not None:
        statement = statement.limit(args.limit)

    rows = (await session.scalars(statement)).all()
    return [CourseRow(c.id, c.external_id, c.title, c.description) for c in rows]


def _course_id_filter(value: str):  # type: ignore[no-untyped-def]
    """Match one --course-id value against the UUID pk if it parses, else external_id."""
    try:
        return Course.id == uuid.UUID(value)
    except ValueError:
        return Course.external_id == value


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def map_course(client: AsyncOpenAI, system_prompt: str, course: CourseRow) -> list[str]:
    """Ask the model which skills the course teaches; return the raw id list."""
    user_prompt = f"Course title: {course.title}\nCourse description: {course.description or ''}"
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    skill_ids = data.get("skill_ids", [])
    if not isinstance(skill_ids, list):
        return []
    return [s for s in skill_ids if isinstance(s, str)]


async def replace_course_skills(session, course_id: uuid.UUID, skill_ids: list[str]) -> None:  # type: ignore[no-untyped-def]
    """Replace a course's skill rows (delete then insert) so re-runs are idempotent."""
    await session.execute(delete(CourseSkill).where(CourseSkill.course_id == course_id))
    for skill_id in skill_ids:
        session.add(CourseSkill(course_id=course_id, skill_id=skill_id))


def report(mappings: list[Mapping], args: argparse.Namespace) -> None:
    total = len(mappings)
    if total == 0:
        print("Nothing to map — every course already has skills (or none matched the filter).")
        return

    skill_counts = [len(m.accepted) for m in mappings]
    zero_skills = sum(1 for n in skill_counts if n == 0)
    over_ten = sum(1 for n in skill_counts if n > 10)
    dropped_total = sum(len(m.dropped) for m in mappings)
    print("\n=== summary ===")
    print(f"courses mapped: {total}")
    print(f"avg skills/course: {sum(skill_counts) / total:.2f}")
    print(f"got 0 skills: {zero_skills} | got >10: {over_ten}")
    print(f"hallucinated ids dropped by validation: {dropped_total}")

    sample_count = 10 if args.dry_run else 5
    print(f"\n=== {min(sample_count, total)} sample mappings ===")
    for mapping in mappings[:sample_count]:
        course = mapping.course
        print(f"\n• {course.title}  ({course.external_id})")
        print(f"  desc: {course.description}")
        print(f"  skills: {mapping.accepted}")


if __name__ == "__main__":
    main()
