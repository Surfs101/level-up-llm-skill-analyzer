"""DTOs for the analyze trigger and the run poller.

The frontend running screen shows a 6-stage list (see frontend .../running/[id] and
components/app/StageList), but the pipeline has 8 steps. `ui_stage` maps the backend
`current_stage` (1..8) to the StageList's 0-indexed active stage (0..5), and 6 when
the run is done (which tells the UI all stages are complete → navigate to the plan).

The mapping folds ingest+extract_text into "Parsing your resume" and retrieve+select
into "Picking your courses"; the JD-reading stage has no dedicated backend step (the
matcher reads resume and JD together in step 3), so it advances through.
"""

import uuid
from typing import Any

from pydantic import BaseModel

from app.models import Run
from app.schemas.plans import PlanDetail

# backend current_stage (1..8) -> StageList active index (0..5).
#   0 Parsing your resume     1 Extracting your skills   2 Reading the job description
#   3 Finding the gap         4 Picking your courses     5 Generating your projects
_STEP_TO_UI_STAGE = {1: 0, 2: 0, 3: 1, 4: 3, 5: 4, 6: 4, 7: 5, 8: 5}
_UI_STAGE_COUNT = 6  # StageList >= this many → every stage done


class AnalyzeResponse(BaseModel):
    run_id: uuid.UUID


class RunStatusResponse(BaseModel):
    run_id: uuid.UUID
    status: str  # queued | running | completed | failed
    current_stage: int | None  # backend step 1..8 (null before it starts)
    ui_stage: int  # StageList active index; 6 = all done
    error_message: str | None
    # For a signed-in run: the saved Plan's id (the UI navigates to /plans/{id}).
    plan_id: uuid.UUID | None = None
    # For a guest run: the plan payload inline (guests have no Plan row / GET /plans).
    plan: PlanDetail | None = None

    @classmethod
    def from_run(cls, run: Run, plan_id: uuid.UUID | None = None) -> "RunStatusResponse":
        return cls(
            run_id=run.id,
            status=run.status,
            current_stage=run.current_stage,
            ui_stage=_ui_stage(run.status, run.current_stage),
            error_message=run.error_message,
            plan_id=plan_id,
        )

    @classmethod
    def from_guest(cls, run_id: uuid.UUID, record: dict[str, Any]) -> "RunStatusResponse":
        status = record["status"]
        current_stage = record.get("current_stage")
        plan_payload = record.get("plan")
        return cls(
            run_id=run_id,
            status=status,
            current_stage=current_stage,
            ui_stage=_ui_stage(status, current_stage),
            error_message=record.get("error_message"),
            plan_id=None,
            plan=PlanDetail.model_validate(plan_payload) if plan_payload is not None else None,
        )


def _ui_stage(status: str, current_stage: int | None) -> int:
    if status == "completed":
        return _UI_STAGE_COUNT  # all stages done → the UI navigates to the plan
    if current_stage is None:
        return 0  # queued, not started
    return _STEP_TO_UI_STAGE.get(current_stage, 0)
