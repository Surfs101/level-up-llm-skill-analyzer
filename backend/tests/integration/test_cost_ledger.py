"""Cost ledger — rows are written per call, and the >$0.50/day warning fires.

Needs Postgres (real llm_calls rows). llm_calls.run_id isn't a FK, so tests clean up
their own rows by run_id.
"""

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.llm import client as llm_client
from app.llm import cost_ledger
from app.models import LlmCall, Run, User

SUB_PREFIX = "ledger-test-"


@pytest.fixture
async def maker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping cost-ledger test: {exc}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_record_call_writes_a_row(maker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cost_ledger, "get_sessionmaker", lambda: maker)
    run_id = uuid.uuid4()
    try:
        await cost_ledger.record_call(run_id, "gpt-4o", 1000, 500, 0.0075)

        async with maker() as session:
            row = (await session.scalars(select(LlmCall).where(LlmCall.run_id == run_id))).one()
            assert row.model == "gpt-4o"
            assert row.prompt_tokens == 1000 and row.completion_tokens == 500
            assert row.cost_usd == pytest.approx(0.0075)
    finally:
        await _cleanup(maker, [run_id])


async def test_chat_writes_the_ledger_when_given_a_run_id(maker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cost_ledger, "get_sessionmaker", lambda: maker)

    async def fake_create(**_kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
            usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=500),
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(llm_client, "_client", lambda: fake_client)

    run_id = uuid.uuid4()
    try:
        result = await llm_client.chat(
            [{"role": "user", "content": "x"}], model="gpt-4o", run_id=run_id
        )
        assert result.cost_usd == pytest.approx((1000 * 2.50 + 500 * 10.00) / 1_000_000)

        async with maker() as session:
            row = (await session.scalars(select(LlmCall).where(LlmCall.run_id == run_id))).one()
            assert row.model == "gpt-4o"
    finally:
        await _cleanup(maker, [run_id])


async def test_daily_budget_warning_fires_over_fifty_cents(maker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cost_ledger, "get_sessionmaker", lambda: maker)

    warnings: list[dict] = []
    monkeypatch.setattr(
        cost_ledger.logfire, "warn", lambda msg, **kw: warnings.append({"msg": msg, **kw})
    )

    async with maker() as session:
        user = User(google_sub=f"{SUB_PREFIX}{uuid.uuid4()}", email="l@example.com")
        session.add(user)
        await session.flush()
        run = Run(user_id=user.id, status="completed")
        session.add(run)
        await session.commit()
        user_id, run_id = user.id, run.id

    try:
        # Two calls under budget, then one that tips it over $0.50.
        await cost_ledger.record_call(run_id, "gpt-4o", 0, 0, 0.30)
        assert warnings == []
        await cost_ledger.record_call(run_id, "gpt-4o", 0, 0, 0.30)  # total 0.60 > 0.50

        assert len(warnings) == 1
        assert warnings[0]["user_id"] == str(user_id)
        assert warnings[0]["total_usd"] == pytest.approx(0.60)
    finally:
        await _cleanup(maker, [run_id])
        async with maker() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


async def _cleanup(maker, run_ids: list[uuid.UUID]) -> None:  # type: ignore[no-untyped-def]
    async with maker() as session:
        await session.execute(delete(LlmCall).where(LlmCall.run_id.in_(run_ids)))
        await session.commit()
