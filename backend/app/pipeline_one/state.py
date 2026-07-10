"""The typed object threaded through all 8 Pipeline 1 steps (design §7, §8).

One PipelineState is created when an analysis is triggered and passed step to step.
Each step reads the fields it needs and returns an *updated copy* via
`state.model_copy(update={...})` — the state is frozen, so nothing is mutated in
place. A field is None until the step that produces it has run; the field list below
is roughly in production order.

This makes every step independently testable: build a PipelineState with just the
inputs that step consumes and assert on the copy it returns.
"""

import uuid

from pydantic import BaseModel, ConfigDict


class PipelineState(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Identity — who and which run. user_id is None for guests (Redis-only, no runs row).
    run_id: uuid.UUID
    user_id: uuid.UUID | None = None
    is_guest: bool = False

    # Inputs, present from the start.
    jd_text: str
    filename: str | None = None
    content_type: str | None = None
    # The raw upload, consumed by step 1 (ingest) and dropped once it's staged to R2.
    file_bytes: bytes | None = None

    # Step 1 (ingest) → sha256 + staging key; step 2 (extract) → permanent .txt key.
    file_hash: str | None = None
    r2_staging_key: str | None = None
    r2_text_key: str | None = None

    # Step 2 (extract text) → plain resume text.
    resume_text: str | None = None

    # Step 3 (extract skills) → canonical skill ids from each side.
    resume_skill_ids: list[str] | None = None
    jd_skill_ids: list[str] | None = None

    # Step 4 (gap analysis) → matched/missing sets + fit score. missing is priority-sorted.
    matched_ids: list[str] | None = None
    missing_ids: list[str] | None = None
    fit_score: int | None = None

    # Step 5 (retrieve) → top course candidates; step 6 (select) → the chosen two and
    # which gap skills each covers.
    retrieved_course_ids: list[uuid.UUID] | None = None
    course_a_id: uuid.UUID | None = None
    course_b_id: uuid.UUID | None = None
    course_a_covered: list[str] | None = None
    course_b_covered: list[str] | None = None

    # Step 7 (generate projects) → the two Markdown write-ups.
    project_one_md: str | None = None
    project_two_md: str | None = None
