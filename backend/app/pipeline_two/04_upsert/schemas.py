"""Step 04 output contract."""

from pydantic import BaseModel


class UpsertResult(BaseModel):
    upserted_count: int  # postings written this cycle
