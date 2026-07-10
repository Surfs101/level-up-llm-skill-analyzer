"""Response DTOs for the jobs API (design §9, requirement F6).

Mirrors the frontend's job shape (frontend/lib/mock-data/jobs.ts) with the same
reconciliations as the plans API:

  - Skills are returned as objects {id, display_name, category}, not bare ids, so the
    UI renders a chip for any taxonomy skill without its own lookup table. `matched`
    (the user already has it) and `missing` (the gap) split the posting's skills.
  - `overlap` is the ranking key: how many of the posting's skills the user has (=
    len(matched_skills)). The list is ordered by it (design §9).

Fields with no backend source are derived client-side, not sent:
  - The **company logo tile** is just the first letter of `company` (JobCard renders
    it) — there is no logo in the DB.
  - The "X of Y matched" count uses len(matched) of len(matched)+len(missing); we
    don't send a separate full-skills list because matched ∪ missing already is it.
"""

import uuid

from pydantic import BaseModel

from app.nlp.taxonomy import get_skill_by_id


class SkillRef(BaseModel):
    id: str
    display_name: str
    category: str


class JobMatch(BaseModel):
    id: uuid.UUID
    company: str
    title: str
    location: str | None
    url: str
    posted_at: str  # yyyy-mm-dd
    overlap: int  # skills the user has that this posting wants
    matched_skills: list[SkillRef]
    missing_skills: list[SkillRef]


def skill_refs(skill_ids: list[str]) -> list[SkillRef]:
    return [_skill_ref(skill_id) for skill_id in skill_ids]


def _skill_ref(skill_id: str) -> SkillRef:
    skill = get_skill_by_id(skill_id)
    if skill is None:  # id not in the taxonomy (shouldn't happen for a stored job)
        return SkillRef(id=skill_id, display_name=skill_id, category="")
    return SkillRef(id=skill.id, display_name=skill.canonical_name, category=skill.category)
