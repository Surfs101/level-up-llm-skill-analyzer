"""Step 01 output contract."""

from pydantic import BaseModel


class IngestResult(BaseModel):
    file_hash: str  # sha256 of the original upload
    r2_staging_key: str  # where the binary was staged
