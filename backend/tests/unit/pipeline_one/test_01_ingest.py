"""Step 01 (ingest) — happy path + §15 validation failures."""

import hashlib
import importlib
import uuid

import pytest

from app.common.errors import PipelineStepError
from app.pipeline_one.state import PipelineState

ingest_step = importlib.import_module("app.pipeline_one.01_ingest")


def make_state(file_bytes: bytes | None) -> PipelineState:
    return PipelineState(run_id=uuid.uuid4(), jd_text="a job description", file_bytes=file_bytes)


async def test_valid_upload_is_hashed_and_staged(make_docx, r2, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    file_bytes = make_docx("Python, FastAPI, Docker")
    state = make_state(file_bytes)
    monkeypatch.setattr(ingest_step, "get_r2", lambda: r2)

    result = await ingest_step.run(state)

    assert result.file_hash == hashlib.sha256(file_bytes).hexdigest()
    assert result.r2_staging_key == f"staging/{state.run_id}.bin"
    assert result.file_bytes is None  # dropped once staged
    assert await r2.get(result.r2_staging_key) == file_bytes  # really in R2


async def test_oversize_upload_is_rejected(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(ingest_step, "get_r2", lambda: None)  # never reached
    too_big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 1)

    with pytest.raises(PipelineStepError, match="5 MB"):
        await ingest_step.run(make_state(too_big))


async def test_non_document_is_rejected(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(ingest_step, "get_r2", lambda: None)  # never reached

    with pytest.raises(PipelineStepError, match="PDF or"):
        await ingest_step.run(make_state(b"just some plain text, not a real document"))
