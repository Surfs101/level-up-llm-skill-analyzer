"""Step 03 output contract."""

from pydantic import BaseModel


class ExtractSkillsResult(BaseModel):
    resume_skill_ids: list[str]  # canonical ids, sorted
    jd_skill_ids: list[str]  # canonical ids, sorted
