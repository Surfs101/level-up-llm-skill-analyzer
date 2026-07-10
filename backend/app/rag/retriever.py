"""Retrieve candidate courses for a skill gap (pipeline_one step 5).

The gap — the skills the resume is missing for a job — is turned into a query
string from the skills' display names, embedded with the SAME model the corpus was
embedded with (app.llm.embeddings), and matched against course_embeddings by cosine
distance over the HNSW index. The ranker (ranker.py) turns these candidates into the
final two picks.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.embeddings import embed_text
from app.models import Course, CourseEmbedding, CourseSkill
from app.nlp.taxonomy import get_skill_by_id

TOP_K = 50


@dataclass(frozen=True)
class CandidateCourse:
    id: uuid.UUID
    external_id: str
    title: str
    url: str
    duration_hours: Decimal | None
    skill_ids: frozenset[str]


def build_query_text(missing_skill_ids: list[str]) -> str:
    """The retrieval query: the missing skills' display names, comma-joined.

    Display names (canonical_name) read more like course text than slugs do; an id
    with no taxonomy entry falls back to the slug itself.
    """
    names = []
    for skill_id in missing_skill_ids:
        skill = get_skill_by_id(skill_id)
        names.append(skill.canonical_name if skill else skill_id)
    return ", ".join(names)


async def retrieve_candidates(
    session: AsyncSession, missing_skill_ids: list[str], top_k: int = TOP_K
) -> list[CandidateCourse]:
    """The cosine-nearest courses to the gap, each carrying its mapped skill set."""
    if not missing_skill_ids:
        return []

    query_vector = await embed_text(build_query_text(missing_skill_ids))
    distance = CourseEmbedding.embedding.cosine_distance(query_vector)
    statement = (
        select(Course)
        .join(CourseEmbedding, CourseEmbedding.course_id == Course.id)
        .order_by(distance)
        .limit(top_k)
    )
    courses = list((await session.scalars(statement)).all())
    skills_by_course = await _load_skill_sets(session, [course.id for course in courses])
    return _build_candidates(courses, skills_by_course)


async def load_candidates_by_ids(
    session: AsyncSession, course_ids: list[uuid.UUID]
) -> list[CandidateCourse]:
    """Rebuild CandidateCourses for a known set of course ids, order preserved.

    Step 5 stores only the retrieved ids on the pipeline state; step 6 calls this to
    get the full candidates (skill sets, duration) it needs to rank — without
    re-embedding or re-querying pgvector.
    """
    if not course_ids:
        return []
    courses = list((await session.scalars(select(Course).where(Course.id.in_(course_ids)))).all())
    skills_by_course = await _load_skill_sets(session, [course.id for course in courses])
    by_id = {course.id: course for course in courses}
    ordered = [by_id[course_id] for course_id in course_ids if course_id in by_id]
    return _build_candidates(ordered, skills_by_course)


def _build_candidates(
    courses: list[Course], skills_by_course: dict[uuid.UUID, frozenset[str]]
) -> list[CandidateCourse]:
    return [
        CandidateCourse(
            id=course.id,
            external_id=course.external_id,
            title=course.title,
            url=course.url,
            duration_hours=course.duration_hours,
            skill_ids=skills_by_course.get(course.id, frozenset()),
        )
        for course in courses
    ]


async def _load_skill_sets(
    session: AsyncSession, course_ids: list[uuid.UUID]
) -> dict[uuid.UUID, frozenset[str]]:
    """Fetch every course's skill set in one query, keyed by course id."""
    if not course_ids:
        return {}
    rows = await session.scalars(select(CourseSkill).where(CourseSkill.course_id.in_(course_ids)))
    sets: dict[uuid.UUID, set[str]] = {}
    for course_skill in rows:
        sets.setdefault(course_skill.course_id, set()).add(course_skill.skill_id)
    return {course_id: frozenset(skill_ids) for course_id, skill_ids in sets.items()}
