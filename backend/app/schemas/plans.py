"""Response DTOs for the plans API.

These mirror the frontend's plan shape (frontend/lib/mock-data/plans.ts) with three
deliberate reconciliations to what the DB actually stores (design §6):

  - Skills are returned as objects {id, display_name, category}, not bare ids, so the
    UI can render a chip for any taxonomy skill without its own lookup table.
  - Courses embed their display fields (title/provider/description/url) because there
    is no separate courses endpoint yet; each also carries the covered skills it buys.
  - Projects are the stored Markdown (project_one_md / project_two_md) — step 7 emits
    Markdown, so that's what we return. (The mock assumed pre-structured projects.)

Fields the DB has no source for — jd_title, jd_company, resume_filename — are omitted;
the list view derives a heading from jd_text. Wiring those up needs a schema + pipeline
change (extract company/title, persist the filename), tracked as a follow-up.
"""

import uuid

from pydantic import BaseModel

from app.models import Course, Plan
from app.nlp.taxonomy import get_skill_by_id


class SkillRef(BaseModel):
    id: str
    display_name: str
    category: str


class PlanCourseRef(BaseModel):
    course_id: uuid.UUID
    rank: int  # 1 = Course A, 2 = Course B
    title: str
    provider: str
    description: str | None
    url: str
    skills_covered: list[SkillRef]


class PlanSummary(BaseModel):
    """One row in the saved-plans list."""

    id: uuid.UUID
    jd_text: str
    created_at: str  # yyyy-mm-dd
    fit_score: int
    matched_count: int
    missing_count: int

    @classmethod
    def from_plan(cls, plan: Plan) -> "PlanSummary":
        return cls(
            id=plan.id,
            jd_text=plan.jd_text,
            created_at=plan.created_at.date().isoformat(),
            fit_score=plan.fit_score,
            matched_count=len(plan.matched_skill_ids),
            missing_count=len(plan.missing_skill_ids),
        )


class PlanDetail(BaseModel):
    """One full plan."""

    id: uuid.UUID
    jd_text: str
    created_at: str
    fit_score: int
    matched_skills: list[SkillRef]
    missing_skills: list[SkillRef]
    courses: list[PlanCourseRef]
    project_one_md: str
    project_two_md: str

    @classmethod
    def from_plan(cls, plan: Plan, courses_by_id: dict[uuid.UUID, Course]) -> "PlanDetail":
        return cls.from_parts(
            plan_id=plan.id,
            jd_text=plan.jd_text,
            created_at=plan.created_at.date().isoformat(),
            fit_score=plan.fit_score,
            matched_skill_ids=plan.matched_skill_ids,
            missing_skill_ids=plan.missing_skill_ids,
            course_a_id=plan.course_a_id,
            course_b_id=plan.course_b_id,
            course_a_covered=plan.course_a_covered,
            course_b_covered=plan.course_b_covered,
            project_one_md=plan.project_one_md,
            project_two_md=plan.project_two_md,
            courses_by_id=courses_by_id,
        )

    @classmethod
    def from_parts(
        cls,
        *,
        plan_id: uuid.UUID,
        jd_text: str,
        created_at: str,
        fit_score: int,
        matched_skill_ids: list[str],
        missing_skill_ids: list[str],
        course_a_id: uuid.UUID | None,
        course_b_id: uuid.UUID | None,
        course_a_covered: list[str],
        course_b_covered: list[str],
        project_one_md: str,
        project_two_md: str,
        courses_by_id: dict[uuid.UUID, Course],
    ) -> "PlanDetail":
        """Build from raw fields — used by from_plan (a Plan row) and by the guest
        path (which has no Plan row, just the pipeline state)."""
        courses = []
        picks = [
            (course_a_id, 1, course_a_covered),
            (course_b_id, 2, course_b_covered),
        ]
        for course_id, rank, covered in picks:
            course = courses_by_id.get(course_id) if course_id is not None else None
            if course is None:
                continue  # a fallback pick with no course row, or a deleted course
            courses.append(
                PlanCourseRef(
                    course_id=course.id,
                    rank=rank,
                    title=course.title,
                    provider=course.platform,
                    description=course.description,
                    url=course.url,
                    skills_covered=_skill_refs(covered),
                )
            )

        return cls(
            id=plan_id,
            jd_text=jd_text,
            created_at=created_at,
            fit_score=fit_score,
            matched_skills=_skill_refs(matched_skill_ids),
            missing_skills=_skill_refs(missing_skill_ids),
            courses=courses,
            project_one_md=project_one_md,
            project_two_md=project_two_md,
        )


def _skill_refs(skill_ids: list[str]) -> list[SkillRef]:
    return [_skill_ref(skill_id) for skill_id in skill_ids]


def _skill_ref(skill_id: str) -> SkillRef:
    skill = get_skill_by_id(skill_id)
    if skill is None:  # id not in the taxonomy (shouldn't happen for a saved plan)
        return SkillRef(id=skill_id, display_name=skill_id, category="")
    return SkillRef(id=skill.id, display_name=skill.canonical_name, category=skill.category)
