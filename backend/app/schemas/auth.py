"""Response DTOs for the auth routes.

Field names are snake_case to match the rest of the API the frontend already
consumes (e.g. the skills payload uses `canonical_name`, `priority_rank`). The
frontend's avatar menu needs a display name, an email, and an avatar image — this
is the shape /me returns.
"""

import uuid

from pydantic import BaseModel, ConfigDict


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
