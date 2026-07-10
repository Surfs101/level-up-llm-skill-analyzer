"""Plans routes — read and delete saved plans. HTTP only.

Every query is scoped to the current user. Plans are immutable snapshots, so there is
no update — DELETE removes a plan, it never mutates one.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.csrf import require_csrf
from app.deps import get_current_user, get_db
from app.models import Course, Plan, User
from app.schemas.plans import PlanDetail, PlanSummary

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=list[PlanSummary])
async def list_plans(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanSummary]:
    statement = (
        select(Plan)
        .where(Plan.user_id == user.id)
        .order_by(Plan.created_at.desc())  # uses idx_plans_user_created
        .limit(limit)
        .offset(offset)
    )
    plans = (await db.scalars(statement)).all()
    return [PlanSummary.from_plan(plan) for plan in plans]


@router.get("/plans/{plan_id}", response_model=PlanDetail)
async def get_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanDetail:
    plan = await db.get(Plan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Plan not found")

    courses_by_id = await _load_courses(db, [plan.course_a_id, plan.course_b_id])
    return PlanDetail.from_plan(plan, courses_by_id)


@router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    plan = await db.get(Plan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Plan not found")
    await db.delete(plan)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _load_courses(
    db: AsyncSession, course_ids: list[uuid.UUID | None]
) -> dict[uuid.UUID, Course]:
    ids = [course_id for course_id in course_ids if course_id is not None]
    if not ids:
        return {}
    courses = (await db.scalars(select(Course).where(Course.id.in_(ids)))).all()
    return {course.id: course for course in courses}
