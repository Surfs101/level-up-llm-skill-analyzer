"""Step 01 — Ingest. Public entry point: run(state) -> state.

Validates the uploaded resume, hashes it, and stages the binary to R2. Drops
file_bytes from the state afterward — once it's in R2 the raw upload has no reason
to keep riding along in memory.
"""

from app.common.errors import PipelineStepError
from app.pipeline_one.state import PipelineState
from app.storage.r2 import get_r2

from .logic import ingest


async def run(state: PipelineState) -> PipelineState:
    if state.file_bytes is None:
        raise PipelineStepError("No file was uploaded.")
    result = await ingest(state.file_bytes, state.run_id, get_r2())
    return state.model_copy(update={**result.model_dump(), "file_bytes": None})
