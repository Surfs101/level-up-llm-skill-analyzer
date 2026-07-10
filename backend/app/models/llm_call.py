"""LLM cost ledger (design §12).

One row per OpenAI chat call: which run it was for, the model, token usage, and the
computed cost. `run_id` is a plain nullable column, NOT a foreign key — a guest run has
a run_id but no `runs` row, and this ledger is append-only observability, not
referential data. A daily aggregate (see app/llm/cost_ledger.py) powers the
per-user spend warning.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # not a FK (guests)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
