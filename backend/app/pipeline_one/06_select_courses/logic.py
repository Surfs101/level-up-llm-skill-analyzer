"""Step 06 logic — pick Course A and Course B for the gap (design §8 step 6, §15).

The primary ranking is the shared, priority-weighted ranker (app/rag/ranker.py):
weight {1:4, 2:3, 3:2, 4:1} by priority_rank, tie-broken by raw coverage count, then
shorter duration, then external_id. Note the deliberate asymmetry (§8): the gap is
DISPLAYED languages-first, but in scoring a language gap is worth the MOST (weight 4).

If that yields fewer than two courses (no/one candidate covers an exact missing
skill), we fill the empty slot(s) with a looser fallback: courses whose skills touch
the same taxonomy CATEGORIES as the gap, best category-overlap first (§15). Either
way, course_*_covered is the exact set of missing skills the chosen course teaches —
which may be empty for a fallback pick.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.nlp.taxonomy import get_skill_by_id
from app.rag.ranker import rank_courses
from app.rag.retriever import CandidateCourse, load_candidates_by_ids

from .schemas import SelectResult


async def choose_courses(
    session: AsyncSession, retrieved_course_ids: list[uuid.UUID], missing_skill_ids: list[str]
) -> SelectResult:
    candidates = await load_candidates_by_ids(session, retrieved_course_ids)
    return select_from_candidates(candidates, missing_skill_ids)


def select_from_candidates(
    candidates: list[CandidateCourse], missing_skill_ids: list[str]
) -> SelectResult:
    ranked = rank_courses(candidates, missing_skill_ids)
    chosen = [entry.course for entry in ranked[:2]]
    if len(chosen) < 2:
        chosen = _fill_from_category_fallback(chosen, candidates, missing_skill_ids)

    course_a = chosen[0] if chosen else None
    course_b = chosen[1] if len(chosen) > 1 else None
    missing = set(missing_skill_ids)
    return SelectResult(
        course_a_id=course_a.id if course_a else None,
        course_b_id=course_b.id if course_b else None,
        course_a_covered=sorted(course_a.skill_ids & missing) if course_a else [],
        course_b_covered=sorted(course_b.skill_ids & missing) if course_b else [],
    )


def _fill_from_category_fallback(
    chosen: list[CandidateCourse],
    candidates: list[CandidateCourse],
    missing_skill_ids: list[str],
) -> list[CandidateCourse]:
    """Top up `chosen` to two courses by taxonomy-category overlap with the gap.

    Used only when exact-coverage ranking gave fewer than two picks. Courses sharing
    no category with the gap are skipped; ties break on external_id for determinism.
    """
    already = {course.id for course in chosen}
    gap_categories = _categories_of(missing_skill_ids)

    scored = []
    for candidate in candidates:
        if candidate.id in already:
            continue
        overlap = len(gap_categories & _categories_of(candidate.skill_ids))
        if overlap == 0:
            continue
        scored.append((overlap, candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1].external_id))

    filled = list(chosen)
    for _, candidate in scored:
        if len(filled) >= 2:
            break
        filled.append(candidate)
    return filled


def _categories_of(skill_ids: frozenset[str] | list[str]) -> set[str]:
    categories = set()
    for skill_id in skill_ids:
        skill = get_skill_by_id(skill_id)
        if skill is not None:
            categories.add(skill.category)
    return categories
