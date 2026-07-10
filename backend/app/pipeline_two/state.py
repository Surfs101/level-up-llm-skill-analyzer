"""The typed object threaded through all 5 Pipeline 2 steps (design §7, §9).

One JobsRefreshState is created when the jobs cron fires and passed step to step:
fetch → filter → extract skills → upsert → purge. Each step reads what it needs and
returns an *updated copy* via `state.model_copy(update={...})`; the state is frozen,
so nothing is mutated in place. A field is None until the step that produces it runs.

Like Pipeline 1's PipelineState, this makes each step testable with a hand-built
state fixture.
"""

from pydantic import BaseModel, ConfigDict

from app.greenhouse.client import GreenhousePosting


class JobsRefreshState(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Input: the allowlisted company slugs to fetch this cycle.
    companies: list[str]

    # Step 1 (fetch) → every raw posting pulled from Greenhouse.
    fetched: list[GreenhousePosting] | None = None

    # Step 2 (filter) → postings kept: ≤ 21 days old AND US/Canada.
    filtered: list[GreenhousePosting] | None = None

    # Step 3 (extract skills) → canonical skill ids per posting, keyed "company/gh_job_id".
    skills_by_job: dict[str, list[str]] | None = None

    # Step 4 (upsert) → how many postings were written.
    upserted_count: int | None = None

    # Step 5 (purge) → how many stale postings were deleted.
    purged_count: int | None = None
