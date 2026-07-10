"""Step 05 output contract."""

from pydantic import BaseModel


class PurgeResult(BaseModel):
    purged_count: int  # postings deleted for being older than the window
