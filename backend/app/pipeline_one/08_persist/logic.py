"""Step 08 logic — persist the plan and complete the run (design §8 step 8).

For a signed-in user, persist() writes the immutable Plan snapshot, completes the run,
and merges the resume's extracted skills into the user's dashboard (the F5 merge). For a
guest, persist_guest() writes the plan payload into their Redis record — no DB rows.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_sessionmaker
from app.db.redis import get_redis_client
from app.guest_runs import save_guest_plan
from app.models import Course, Plan, Run, UserSkill
from app.pipeline_one.state import PipelineState
from app.schemas.plans import PlanDetail

from .schemas import PersistResult

FINAL_STAGE = 8


async def persist(session: AsyncSession, state: PipelineState) -> PersistResult:
    assert state.user_id is not None  # authenticated path only

    plan = Plan(
        user_id=state.user_id,
        run_id=state.run_id,
        jd_text=state.jd_text,
        resume_text_snapshot=state.resume_text or "",
        matched_skill_ids=state.matched_ids or [],
        missing_skill_ids=state.missing_ids or [],
        fit_score=state.fit_score if state.fit_score is not None else 0,
        course_a_id=state.course_a_id,
        course_b_id=state.course_b_id,
        course_a_covered=state.course_a_covered or [],
        course_b_covered=state.course_b_covered or [],
        project_one_md=state.project_one_md or "",
        project_two_md=state.project_two_md or "",
    )
    session.add(plan)

    run = await session.get(Run, state.run_id)
    if run is not None:
        run.status = "completed"
        run.current_stage = FINAL_STAGE
        run.completed_at = datetime.now(UTC)

    await _merge_extracted_skills(session, state.user_id, state.resume_skill_ids or [])

    await session.commit()
    return PersistResult(plan_id=plan.id)


async def _merge_extracted_skills(
    session: AsyncSession, user_id: uuid.UUID, extracted_ids: list[str]
) -> None:
    """F5 merge (§6): replace the user's 'extracted' partition with this resume's skills,
    leaving 'manual' rows untouched — so re-analyzing refreshes, never appends."""
    await session.execute(
        delete(UserSkill).where(UserSkill.user_id == user_id, UserSkill.source == "extracted")
    )
    for skill_id in extracted_ids:
        # on_conflict_do_nothing: if the user already added this skill manually, keep
        # their manual row (the PK is (user_id, skill_id), so one row per skill).
        await session.execute(
            pg_insert(UserSkill)
            .values(user_id=user_id, skill_id=skill_id, source="extracted")
            .on_conflict_do_nothing(index_elements=["user_id", "skill_id"])
        )


async def persist_guest(state: PipelineState) -> None:
    """Write the finished plan into the guest's Redis record — no DB rows for guests."""
    courses_by_id = await _load_courses(state.course_a_id, state.course_b_id)
    plan = PlanDetail.from_parts(
        plan_id=state.run_id,
        jd_text=state.jd_text,
        created_at=datetime.now(UTC).date().isoformat(),
        fit_score=state.fit_score if state.fit_score is not None else 0,
        matched_skill_ids=state.matched_ids or [],
        missing_skill_ids=state.missing_ids or [],
        course_a_id=state.course_a_id,
        course_b_id=state.course_b_id,
        course_a_covered=state.course_a_covered or [],
        course_b_covered=state.course_b_covered or [],
        project_one_md=state.project_one_md or "",
        project_two_md=state.project_two_md or "",
        courses_by_id=courses_by_id,
    )
    await save_guest_plan(get_redis_client(), state.run_id, plan.model_dump(mode="json"))


async def _load_courses(
    course_a_id: uuid.UUID | None, course_b_id: uuid.UUID | None
) -> dict[uuid.UUID, Course]:
    """Read-only lookup of the two chosen courses' display fields (no writes)."""
    ids = [course_id for course_id in (course_a_id, course_b_id) if course_id is not None]
    if not ids:
        return {}
    async with get_sessionmaker()() as session:
        courses = (await session.scalars(select(Course).where(Course.id.in_(ids)))).all()
    return {course.id: course for course in courses}
