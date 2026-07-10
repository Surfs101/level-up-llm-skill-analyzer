"""Dashboard routes — the user's editable skill set (design §6, F4/F5).

HTTP only; every query is scoped to the current user, so a user can only ever read
or change their own user_skills rows. PATCH is a non-idempotent write and requires a
CSRF double-submit token (app/common/csrf.py) on top of the SameSite=Lax session.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.csrf import require_csrf
from app.deps import get_current_user, get_db
from app.models import Resume, Skill, User, UserSkill
from app.schemas.dashboard import DashboardPatchRequest, DashboardResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    return await build_dashboard(user, db)


@router.patch("/dashboard", response_model=DashboardResponse, dependencies=[Depends(require_csrf)])
async def patch_dashboard(
    payload: DashboardPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    await add_manual_skills(db, user, payload.add)
    await remove_manual_skills(db, user, payload.remove)
    await db.commit()
    return await build_dashboard(user, db)


async def build_dashboard(user: User, db: AsyncSession) -> DashboardResponse:
    """Read the user's skills, grouped by category with the id list per category."""
    rows = (
        await db.execute(
            select(Skill.id, Skill.category, UserSkill.added_at)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(UserSkill.user_id == user.id)
        )
    ).all()

    skills_by_category: dict[str, list[str]] = {}
    latest: datetime | None = None
    for skill_id, category, added_at in rows:
        skills_by_category.setdefault(category, []).append(skill_id)
        if latest is None or added_at > latest:
            latest = added_at

    # The resume the profile was most recently extracted from (F4/F5); None if the user
    # has only manual skills and has never run an analysis.
    last_updated_from = await db.scalar(
        select(Resume.filename)
        .where(Resume.user_id == user.id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )

    return DashboardResponse(
        last_updated_from=last_updated_from,
        last_updated_at=latest.date().isoformat() if latest else None,
        # Sort ids for a stable response; chip order within a category is cosmetic.
        skills_by_category={cat: sorted(ids) for cat, ids in skills_by_category.items()},
    )


async def add_manual_skills(db: AsyncSession, user: User, skill_ids: list[str]) -> None:
    """Insert each id as a manual skill, rejecting any id not in the taxonomy."""
    if not skill_ids:
        return

    known = set((await db.scalars(select(Skill.id).where(Skill.id.in_(skill_ids)))).all())
    unknown = [skill_id for skill_id in skill_ids if skill_id not in known]
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unknown skill ids: {unknown}",
        )

    for skill_id in skill_ids:
        # If the skill is already on the profile (either source), leave it as is.
        statement = (
            pg_insert(UserSkill)
            .values(user_id=user.id, skill_id=skill_id, source="manual")
            .on_conflict_do_nothing(index_elements=["user_id", "skill_id"])
        )
        await db.execute(statement)


async def remove_manual_skills(db: AsyncSession, user: User, skill_ids: list[str]) -> None:
    """Delete the user's manual rows for these ids. Extracted rows are untouched —
    those are owned by the resume merge (Phase 4), not manual editing."""
    if not skill_ids:
        return

    await db.execute(
        delete(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id.in_(skill_ids),
            UserSkill.source == "manual",
        )
    )
