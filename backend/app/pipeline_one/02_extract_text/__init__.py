"""Step 02 — Extract text. Public entry point: run(state) -> state.

Turns the staged binary into normalized text, persists it as a .txt, and drops the
staging binary. Sets resume_text and r2_text_key on the state.
"""

from app.pipeline_one.state import PipelineState
from app.storage.r2 import get_r2

from .logic import extract_text


async def run(state: PipelineState) -> PipelineState:
    assert state.r2_staging_key is not None  # set by step 01
    assert state.file_hash is not None  # set by step 01
    result = await extract_text(state.r2_staging_key, state.file_hash, get_r2())
    return state.model_copy(update=result.model_dump())
