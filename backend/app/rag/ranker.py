"""Rank candidate courses by priority-weighted gap coverage (pipeline_one step 6).

Every missing skill a course teaches earns points by the skill's priority rank —
covering a language gap (rank 1) is worth more than a technique gap (rank 4),
because the language is the bigger unblock. The two highest-scoring courses become
Course A and Course B.

On a technique-heavy corpus (like our DeepLearning.AI set, almost all rank-3/4)
the weights rarely differentiate, so scores tie often and the tie-break carries the
decision: more raw skills covered wins, then shorter duration, then external_id so
the result is fully deterministic — the same gap always yields the same two courses.
"""

from dataclasses import dataclass

from app.nlp.taxonomy import get_priority_rank
from app.rag.retriever import CandidateCourse

# Weight by priority_rank: rank 1 (language) … rank 4 (technique).
PRIORITY_WEIGHT = {1: 4, 2: 3, 3: 2, 4: 1}


@dataclass(frozen=True)
class RankedCourse:
    course: CandidateCourse
    score: int
    covered: frozenset[str]  # the missing skills this course actually teaches


def rank_courses(
    candidates: list[CandidateCourse], missing_skill_ids: list[str]
) -> list[RankedCourse]:
    """Score and order the candidates that cover at least one missing skill.

    Courses covering nothing are dropped — they can't be recommended for this gap.
    """
    missing = set(missing_skill_ids)
    ranked = []
    for candidate in candidates:
        covered = frozenset(missing & candidate.skill_ids)
        if not covered:
            continue
        score = sum(PRIORITY_WEIGHT[get_priority_rank(skill_id)] for skill_id in covered)
        ranked.append(RankedCourse(candidate, score, covered))
    ranked.sort(key=_sort_key)
    return ranked


def select_courses(
    candidates: list[CandidateCourse], missing_skill_ids: list[str]
) -> tuple[RankedCourse | None, RankedCourse | None]:
    """The top two courses for the gap.

    Returns (None, None) when no candidate covers any gap skill, and (course, None)
    when only one does — slot B simply stays empty, and the caller shows one course.
    """
    ranked = rank_courses(candidates, missing_skill_ids)
    course_a = ranked[0] if ranked else None
    course_b = ranked[1] if len(ranked) > 1 else None
    return course_a, course_b


def _sort_key(ranked: RankedCourse) -> tuple[int, int, bool, float, str]:
    """Best-first order: higher score, then more covered, then shorter duration.

    duration is unknown (NULL) for the whole current corpus, so the trailing
    external_id is what actually makes ties deterministic today.
    """
    course = ranked.course
    duration_unknown = course.duration_hours is None
    duration_value = float(course.duration_hours) if course.duration_hours is not None else 0.0
    return (
        -ranked.score,
        -len(ranked.covered),
        duration_unknown,
        duration_value,
        course.external_id,
    )
