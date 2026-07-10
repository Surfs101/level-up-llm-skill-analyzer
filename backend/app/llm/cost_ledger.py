"""The OpenAI cost ledger (design §12).

The chat client calls record_call() after each completion to append an llm_calls row.
After writing, we check the run's user's spend for the day and log a Logfire warning if
it's over the budget — full alerting is ops, not code. Guest runs (no user) are skipped.
"""

import uuid
from datetime import UTC, date, datetime

import logfire
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_sessionmaker
from app.models import LlmCall, Run

DAILY_BUDGET_USD = 0.50


async def record_call(
    run_id: uuid.UUID,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    """Append one ledger row, then warn if the run's user is over the daily budget."""
    async with get_sessionmaker()() as session:
        session.add(
            LlmCall(
                run_id=run_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
        )
        await session.commit()
        await _warn_if_over_daily_budget(session, run_id)


async def daily_cost_for_user(
    session: AsyncSession, user_id: uuid.UUID, day: date | None = None
) -> float:
    """Total USD this user's runs spent on OpenAI on `day` (default: today, UTC)."""
    day = day or datetime.now(UTC).date()
    total = await session.scalar(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0.0))
        .join(Run, Run.id == LlmCall.run_id)
        .where(Run.user_id == user_id, func.date(LlmCall.created_at) == day)
    )
    return float(total or 0.0)


async def _warn_if_over_daily_budget(session: AsyncSession, run_id: uuid.UUID) -> None:
    user_id = await session.scalar(select(Run.user_id).where(Run.id == run_id))
    if user_id is None:
        return  # guest run — no user to attribute daily spend to
    total = await daily_cost_for_user(session, user_id)
    if total > DAILY_BUDGET_USD:
        logfire.warn("llm.daily_budget_exceeded", user_id=str(user_id), total_usd=total)
