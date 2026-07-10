"""Step 07 output contract."""

from pydantic import BaseModel


class GenerateResult(BaseModel):
    project_one_md: str  # "fast apply" — only the candidate's current skills
    project_two_md: str  # "skillbridge" — current skills + the course's skills
