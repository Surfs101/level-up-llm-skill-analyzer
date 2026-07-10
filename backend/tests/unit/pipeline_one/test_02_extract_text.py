"""Step 02 (extract text) — PDF + DOCX happy paths, and the §15 unreadable failure."""

import importlib
import uuid

import pytest
from botocore.exceptions import ClientError

from app.common.errors import PipelineStepError
from app.pipeline_one.state import PipelineState

extract_step = importlib.import_module("app.pipeline_one.02_extract_text")

FILE_HASH = "deadbeef"


def make_state() -> PipelineState:
    return PipelineState(
        run_id=uuid.uuid4(),
        jd_text="a job description",
        r2_staging_key=f"staging/{uuid.uuid4()}.bin",
        file_hash=FILE_HASH,
    )


async def _stage(r2, key: str, data: bytes) -> None:  # type: ignore[no-untyped-def]
    await r2.put(key, data, content_type="application/octet-stream")


async def test_extracts_docx_text_and_removes_the_binary(make_docx, r2, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    state = make_state()
    await _stage(r2, state.r2_staging_key, make_docx("Python FastAPI Docker"))
    monkeypatch.setattr(extract_step, "get_r2", lambda: r2)

    result = await extract_step.run(state)

    assert "Python FastAPI Docker" in result.resume_text
    assert result.r2_text_key == f"resumes/{FILE_HASH}.txt"
    assert (await r2.get(result.r2_text_key)).decode() == result.resume_text
    with pytest.raises(ClientError):  # staging binary was deleted
        await r2.get(state.r2_staging_key)


async def test_extracts_pdf_text(make_pdf, r2, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    state = make_state()
    await _stage(r2, state.r2_staging_key, make_pdf("Python FastAPI Docker"))
    monkeypatch.setattr(extract_step, "get_r2", lambda: r2)

    result = await extract_step.run(state)

    assert "Python FastAPI Docker" in result.resume_text


async def test_unparseable_file_fails_the_run(r2, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    state = make_state()
    # Looks like a PDF to the magic-byte check but has no valid structure.
    await _stage(r2, state.r2_staging_key, b"%PDF-1.4 this is not really a pdf")
    monkeypatch.setattr(extract_step, "get_r2", lambda: r2)

    with pytest.raises(PipelineStepError, match="couldn't read"):
        await extract_step.run(state)
