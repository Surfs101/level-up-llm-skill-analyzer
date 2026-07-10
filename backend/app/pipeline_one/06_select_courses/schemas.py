"""Step 06 output contract."""

import uuid

from pydantic import BaseModel


class SelectResult(BaseModel):
    course_a_id: uuid.UUID | None
    course_b_id: uuid.UUID | None
    # The missing skills each chosen course actually teaches — feeds step 07.
    course_a_covered: list[str]
    course_b_covered: list[str]
