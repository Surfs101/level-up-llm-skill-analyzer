"""Step 02 output contract."""

from pydantic import BaseModel

from app.greenhouse.client import GreenhousePosting


class FilterResult(BaseModel):
    filtered: list[GreenhousePosting]
