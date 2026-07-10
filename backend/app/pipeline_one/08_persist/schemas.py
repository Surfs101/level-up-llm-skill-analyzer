"""Step 08 output contract."""

import uuid

from pydantic import BaseModel


class PersistResult(BaseModel):
    plan_id: uuid.UUID  # the immutable Plan row just written
