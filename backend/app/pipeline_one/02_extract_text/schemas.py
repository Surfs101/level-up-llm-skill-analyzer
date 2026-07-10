"""Step 02 output contract."""

from pydantic import BaseModel


class ExtractTextResult(BaseModel):
    resume_text: str  # whitespace-normalized plain text
    r2_text_key: str  # where the .txt was written
