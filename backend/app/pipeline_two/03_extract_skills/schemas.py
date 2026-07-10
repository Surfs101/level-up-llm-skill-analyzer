"""Step 03 output contract."""

from pydantic import BaseModel


class ExtractResult(BaseModel):
    # canonical skill ids per posting, keyed "company/gh_job_id"
    skills_by_job: dict[str, list[str]]
