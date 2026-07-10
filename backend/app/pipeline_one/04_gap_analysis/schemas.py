"""Step 04 output contract."""

from pydantic import BaseModel


class GapResult(BaseModel):
    matched_ids: list[str]  # resume ∩ jd, sorted
    missing_ids: list[str]  # jd − resume, priority-sorted (languages first)
    fit_score: int  # 0..100
