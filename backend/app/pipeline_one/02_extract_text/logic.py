"""Step 02 logic — staged binary -> clean text, kept as a .txt (design §8 step 2).

Read the staged binary back from R2, parse it (pypdf for PDF, python-docx for DOCX),
normalize the whitespace with the same cleaner the matcher uses, write the .txt to a
permanent content-addressed key, and delete the staging binary so no raw resume is
retained (§11).
"""

import io

from docx import Document
from pypdf import PdfReader

from app.common.errors import PipelineStepError
from app.common.files import detect_document_kind
from app.nlp.text_clean import normalize
from app.storage.r2 import R2Storage

from .schemas import ExtractTextResult

UNREADABLE = "we couldn't read this file — try re-saving as PDF"


async def extract_text(staging_key: str, file_hash: str, storage: R2Storage) -> ExtractTextResult:
    data = await storage.get(staging_key)
    text = normalize(_parse(data))
    if not text:
        # Parsed fine but yielded nothing — e.g. a scanned PDF with no text layer.
        raise PipelineStepError(UNREADABLE)

    text_key = f"resumes/{file_hash}.txt"
    await storage.put(text_key, text.encode("utf-8"), content_type="text/plain; charset=utf-8")
    await storage.delete(staging_key)
    return ExtractTextResult(resume_text=text, r2_text_key=text_key)


def _parse(data: bytes) -> str:
    kind = detect_document_kind(data)
    try:
        if kind == "pdf":
            return _parse_pdf(data)
        if kind == "docx":
            return _parse_docx(data)
    except Exception as exc:  # a corrupt/unsupported file that slipped past step 01
        raise PipelineStepError(UNREADABLE) from exc
    raise PipelineStepError(UNREADABLE)


def _parse_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
