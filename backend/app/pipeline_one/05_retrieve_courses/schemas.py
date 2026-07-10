"""Step 05 output contract."""

import uuid

from pydantic import BaseModel


class RetrieveResult(BaseModel):
    retrieved_course_ids: list[uuid.UUID]  # cosine-nearest candidates, up to 50
