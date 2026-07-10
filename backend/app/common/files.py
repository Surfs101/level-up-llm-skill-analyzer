"""Detect whether an uploaded file is really a PDF or DOCX.

We trust the file's magic bytes, not its name or the browser-declared content type
(§11): a `.pdf` that isn't actually a PDF is rejected. Steps 1 (validate) and 2
(parse) both branch on the result, so the check lives here rather than in either
step. DOCX is a ZIP under the hood, so when libmagic only reports a generic zip we
confirm it by looking for the tell-tale `word/document.xml` member.
"""

import io
import zipfile

import magic

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# libmagic sometimes sees a DOCX as just a zip / unknown-binary; we verify those.
_AMBIGUOUS_ZIP_MIMES = {"application/zip", "application/octet-stream"}


def detect_document_kind(data: bytes) -> str | None:
    """Return 'pdf', 'docx', or None if the bytes aren't a real PDF/DOCX."""
    mime = magic.from_buffer(data, mime=True)
    if mime == PDF_MIME:
        return "pdf"
    if mime == DOCX_MIME:
        return "docx"
    if mime in _AMBIGUOUS_ZIP_MIMES and _is_docx_zip(data):
        return "docx"
    return None


def _is_docx_zip(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False
