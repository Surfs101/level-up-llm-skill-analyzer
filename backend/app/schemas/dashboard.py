"""Request/response DTOs for the dashboard skill-set endpoints.

The GET response mirrors the frontend's mock (frontend/lib/mock-data/dashboard.ts)
field-for-field so the UI can swap its mock for a fetch with no screen changes:

    { last_updated_from, last_updated_at, skills_by_category }

`skills_by_category` maps a category to a list of skill *ids* (not richer objects) —
that is exactly what the mock holds, and the frontend resolves each id to a display
name itself. Categories with no skills are omitted. The per-skill source
(extracted|manual) is tracked in the DB and honored by PATCH, but it isn't part of
this response because the frontend doesn't render it.

PATCH deals only in skill *ids*, never surface strings — an id the taxonomy doesn't
know is rejected.
"""

from pydantic import BaseModel, Field


class DashboardResponse(BaseModel):
    # The resume the profile was last extracted from. None until Phase 4 populates
    # the extracted partition (resume upload); manual-only profiles have no resume.
    last_updated_from: str | None
    last_updated_at: str | None  # yyyy-mm-dd, the most recent skill change
    skills_by_category: dict[str, list[str]]


class DashboardPatchRequest(BaseModel):
    # Skill ids to add as manual skills, and manual skill ids to remove. Both
    # default to empty so a caller can send just one side.
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
