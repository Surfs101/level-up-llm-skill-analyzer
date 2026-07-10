"""Dependency health checks for /healthz and /readyz (design §12).

Each check returns a plain bool and never raises — an unreachable dependency is a
False, not a 500. /healthz uses the liveness pair (Postgres + Redis); /readyz adds the
readiness pair (the taxonomy is loaded and OpenAI authenticates).
"""

from collections.abc import Awaitable
from typing import cast

from openai import AsyncOpenAI
from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_sessionmaker
from app.db.redis import get_redis_client
from app.nlp.taxonomy import get_all_skills


async def check_postgres() -> bool:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    try:
        return bool(await cast("Awaitable[bool]", get_redis_client().ping()))
    except Exception:
        return False


def check_taxonomy() -> bool:
    try:
        return len(get_all_skills()) > 0
    except Exception:
        return False


async def check_openai() -> bool:
    """A cheap authenticated call (models.list) — validates the key without spending."""
    try:
        client = AsyncOpenAI(api_key=get_settings().openai_api_key)
        await client.with_options(timeout=5.0).models.list()
        return True
    except Exception:
        return False
