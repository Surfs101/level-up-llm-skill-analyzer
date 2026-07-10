"""Step 01 logic — validate the upload and stage it to R2 (design §8 step 1, §11).

Validation happens before anything expensive: reject an oversize or non-PDF/DOCX
file up front. Only a file that passes gets hashed and written to a temporary R2
staging key, which step 02 reads and then deletes.
"""

import hashlib
import uuid

from app.common.errors import PipelineStepError
from app.common.files import detect_document_kind
from app.storage.r2 import R2Storage

from .schemas import IngestResult

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB (design §3)

TOO_LARGE = "That file is over 5 MB — please upload a smaller resume."
WRONG_TYPE = "That file isn't a PDF or Word document — please upload a PDF or DOCX."


async def ingest(file_bytes: bytes, run_id: uuid.UUID, storage: R2Storage) -> IngestResult:
    _validate(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    staging_key = f"staging/{run_id}.bin"
    await storage.put(staging_key, file_bytes, content_type="application/octet-stream")
    return IngestResult(file_hash=file_hash, r2_staging_key=staging_key)


def _validate(file_bytes: bytes) -> None:
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise PipelineStepError(TOO_LARGE)
    if detect_document_kind(file_bytes) is None:
        raise PipelineStepError(WRONG_TYPE)
