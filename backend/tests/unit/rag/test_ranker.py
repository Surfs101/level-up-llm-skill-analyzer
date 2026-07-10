"""Unit tests for the course ranker — pure, no database.

Courses are hand-built CandidateCourse objects. Priority ranks come from the
taxonomy file (skills.json), not the DB, so these run anywhere. Skills used and
their ranks: python=1, fastapi/pytorch=2, docker/aws=3, rag/machine-learning=4.
"""

import uuid
from decimal import Decimal

from app.rag.ranker import rank_courses, select_courses
from app.rag.retriever import CandidateCourse


def make_course(
    external_id: str, skills: set[str], duration: Decimal | None = None
) -> CandidateCourse:
    return CandidateCourse(
        id=uuid.uuid4(),
        external_id=external_id,
        title=external_id,
        url=f"https://example.com/{external_id}",
        duration_hours=duration,
        skill_ids=frozenset(skills),
    )


def test_score_sums_priority_weights() -> None:
    # python(rank1->4) + machine-learning(rank4->1) = 5; covered is the gap ∩ skills.
    course = make_course("c", {"python", "machine-learning", "unrelated-extra"})
    [ranked] = rank_courses([course], ["python", "machine-learning"])
    assert ranked.score == 5
    assert ranked.covered == frozenset({"python", "machine-learning"})


def test_priority_weight_drives_selection() -> None:
    # A language gap (weight 4) outranks a technique gap (weight 1), regardless of
    # input order.
    gap = ["python", "machine-learning"]
    language_course = make_course("language", {"python"})
    technique_course = make_course("technique", {"machine-learning"})
    course_a, course_b = select_courses([technique_course, language_course], gap)
    assert course_a is not None and course_b is not None
    assert course_a.course.external_id == "language" and course_a.score == 4
    assert course_b.course.external_id == "technique" and course_b.score == 1


def test_tiebreak_coverage_count() -> None:
    # Equal score (4 == 2+2), so the course covering MORE skills wins.
    gap = ["python", "docker", "aws"]  # ranks 1, 3, 3 -> weights 4, 2, 2
    one_skill = make_course("one", {"python"})  # score 4, covers 1
    two_skills = make_course("two", {"docker", "aws"})  # score 4, covers 2
    course_a, course_b = select_courses([one_skill, two_skills], gap)
    assert course_a is not None and course_b is not None
    assert course_a.score == 4 and course_b.score == 4
    assert course_a.course.external_id == "two"  # more coverage breaks the tie


def test_tiebreak_shorter_duration() -> None:
    # Same score and coverage count -> the shorter course wins.
    gap = ["rag"]
    longer = make_course("longer", {"rag"}, duration=Decimal("10"))
    shorter = make_course("shorter", {"rag"}, duration=Decimal("3"))
    course_a, _ = select_courses([longer, shorter], gap)
    assert course_a is not None and course_a.course.external_id == "shorter"


def test_tiebreak_external_id_is_deterministic() -> None:
    # Same score, coverage, and (NULL) duration -> external_id decides, and the
    # result does not depend on input order: same gap -> same answer every time.
    gap = ["rag"]
    z_course = make_course("z-course", {"rag"})
    a_course = make_course("a-course", {"rag"})
    first = select_courses([z_course, a_course], gap)
    second = select_courses([a_course, z_course], gap)
    assert first[0] is not None and first[0].course.external_id == "a-course"
    assert first[0].course.external_id == second[0].course.external_id


def test_degenerate_no_course_covers_anything() -> None:
    # A gap the corpus can't serve returns no picks, and does not crash.
    gap = ["rust"]
    course = make_course("c", {"rag", "python"})
    assert rank_courses([course], gap) == []
    assert select_courses([course], gap) == (None, None)


def test_degenerate_single_course_covers() -> None:
    # Exactly one course covers the gap: it fills slot A, slot B stays empty.
    gap = ["rag"]
    covering = make_course("covering", {"rag"})
    not_covering = make_course("not-covering", {"python"})
    course_a, course_b = select_courses([covering, not_covering], gap)
    assert course_a is not None and course_a.course.external_id == "covering"
    assert course_b is None


def test_empty_candidates() -> None:
    assert select_courses([], ["rag"]) == (None, None)
