"""Step 01 output contract."""

from pydantic import BaseModel

from app.greenhouse.client import GreenhousePosting


class FetchResult(BaseModel):
    fetched: list[GreenhousePosting]
