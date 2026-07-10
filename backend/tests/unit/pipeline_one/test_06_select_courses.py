"""Step 06 (select courses) — covered-set, tie-break order, and the <2 fallback.

The ranking/covered/fallback logic is pure and tested against hand-built candidates
(runs everywhere). One DB-backed test drives run() over seeded courses to prove the
load-by-ids wiring (skip-if-no-DB).
"""

import importlib
import uuid
from decimal import Decimal

from app.pipeline_one.state import PipelineState
from app.rag.retriever import CandidateCourse

select_step = importlib.import_module("app.pipeline_one.06_select_courses")
select_logic = importlib.import_module("app.pipeline_one.06_select_courses.logic")

# Real taxonomy ids and their ranks/categories:
#   python (language, 1), fastapi (framework, 2), docker (devops, 3), rag (technique, 4)
#   typescript, java (language)
GAP = ["python", "fastapi", "docker", "rag"]


def candidate(external_id: str, skills: set[str], duration: int | None = None) -> CandidateCourse:
    return CandidateCourse(
        id=uuid.uuid4(),
        external_id=external_id,
        title=external_id,
        url="https://example.com/course",
        duration_hours=Decimal(duration) if duration is not None else None,
        skill_ids=frozenset(skills),
    )


def test_selects_top_two_by_weighted_score_with_correct_covered_sets() -> None:
    course_y = candidate("Y", {"fastapi", "docker"})  # score 3+2 = 5
    course_x = candidate("X", {"python"})  # score 4
    course_z = candidate("Z", {"rag"})  # score 1

    result = select_logic.select_from_candidates([course_z, course_x, course_y], GAP)

    assert result.course_a_id == course_y.id  # highest score
    assert result.course_b_id == course_x.id  # second
    assert result.course_a_covered == ["docker", "fastapi"]  # sorted ∩ missing
    assert result.course_b_covered == ["python"]


def test_tie_break_prefers_shorter_duration_then_unknown_last() -> None:
    # All cover only docker -> equal score (2) and coverage count (1).
    quick = candidate("Q", {"docker"}, duration=5)
    slow = candidate("P", {"docker"}, duration=10)
    unknown = candidate("A", {"docker"}, duration=None)  # ext sorts first, but dur unknown

    result = select_logic.select_from_candidates([unknown, slow, quick], ["docker"])

    assert result.course_a_id == quick.id  # shortest duration wins
    assert result.course_b_id == slow.id  # then longer; unknown-duration sorts last


def test_tie_break_falls_back_to_external_id() -> None:
    # Same score, coverage, and duration -> external_id decides.
    course_b = candidate("B", {"docker"}, duration=5)
    course_a = candidate("A", {"docker"}, duration=5)

    result = select_logic.select_from_candidates([course_b, course_a], ["docker"])

    assert result.course_a_id == course_a.id  # "A" < "B"
    assert result.course_b_id == course_b.id


def test_under_two_exact_picks_fills_from_category_fallback() -> None:
    exact = candidate("E", {"python"})  # covers the gap exactly
    same_category = candidate("F", {"typescript"})  # language, like the gap
    other_category = candidate("G", {"docker"})  # devops — not in this gap's categories

    result = select_logic.select_from_candidates([exact, same_category, other_category], ["python"])

    assert result.course_a_id == exact.id
    assert result.course_a_covered == ["python"]
    assert result.course_b_id == same_category.id  # filled by category overlap
    assert result.course_b_covered == []  # a fallback pick need not cover an exact skill
    # The unrelated-category course is never chosen.
    assert other_category.id not in (result.course_a_id, result.course_b_id)


def test_no_exact_picks_fills_both_from_fallback() -> None:
    lang_one = candidate("G1", {"typescript"})  # language
    lang_two = candidate("G2", {"java"})  # language
    unrelated = candidate("G3", {"docker"})  # devops

    result = select_logic.select_from_candidates([lang_one, lang_two, unrelated], ["python"])

    assert {result.course_a_id, result.course_b_id} == {lang_one.id, lang_two.id}
    assert result.course_a_covered == [] and result.course_b_covered == []


async def test_run_over_seeded_db(course_seeder, db_sessionmaker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    course_y = await course_seeder("test-s6-y", {"fastapi", "docker"})  # score 5
    course_x = await course_seeder("test-s6-x", {"python"})  # score 4
    course_z = await course_seeder("test-s6-z", {"rag"})  # score 1

    monkeypatch.setattr(select_step, "get_sessionmaker", lambda: db_sessionmaker)
    state = PipelineState(
        run_id=uuid.uuid4(),
        jd_text="jd",
        retrieved_course_ids=[course_x, course_y, course_z],
        missing_ids=GAP,
    )

    result = await select_step.run(state)

    assert result.course_a_id == course_y
    assert result.course_b_id == course_x
    assert result.course_a_covered == ["docker", "fastapi"]
    assert result.course_b_covered == ["python"]
