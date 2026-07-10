"""Guest run records in Redis (design §10, requirement F3).

Guests have no Postgres rows. A guest analysis lives entirely in one Redis key,
`guest_run:{run_id}`, with a 1-hour TTL: the pipeline bumps its status/current_stage
as it runs, and step 8 writes the finished plan payload into it instead of a Plan row.
`GET /runs/{id}` reads it back. When the TTL lapses the run is gone — exactly the
"lives only in their tab" model. No user, no ownership: whoever holds the (random)
run_id can read it.

Every function takes the Redis client so it stays unit-testable against fakeredis,
like app/auth/sessions.py. Each write resets the 1-hour TTL, so the finished plan is
readable for an hour after it completes.
"""

import json
import uuid
from collections.abc import Awaitable
from typing import Any, cast

import redis.asyncio as redis

GUEST_TTL_SECONDS = 3600  # 1 hour
_KEY_PREFIX = "guest_run:"


def _key(run_id: uuid.UUID) -> str:
    return f"{_KEY_PREFIX}{run_id}"


async def create_guest_run(client: redis.Redis, run_id: uuid.UUID, jd_text: str) -> None:
    await _write(
        client,
        run_id,
        {
            "status": "queued",
            "current_stage": None,
            "error_message": None,
            "jd_text": jd_text,
            "plan": None,
        },
    )


async def read_guest_run(client: redis.Redis, run_id: uuid.UUID) -> dict[str, Any] | None:
    raw = await cast("Awaitable[str | None]", client.get(_key(run_id)))
    if raw is None:
        return None
    return cast("dict[str, Any]", json.loads(raw))


async def set_guest_stage(client: redis.Redis, run_id: uuid.UUID, stage: int) -> None:
    await _update(client, run_id, {"status": "running", "current_stage": stage})


async def mark_guest_failed(client: redis.Redis, run_id: uuid.UUID, message: str) -> None:
    await _update(client, run_id, {"status": "failed", "error_message": message})


async def save_guest_plan(client: redis.Redis, run_id: uuid.UUID, plan: dict[str, Any]) -> None:
    await _update(client, run_id, {"status": "completed", "current_stage": 8, "plan": plan})


async def _update(client: redis.Redis, run_id: uuid.UUID, changes: dict[str, Any]) -> None:
    record = await read_guest_run(client, run_id)
    if record is None:
        return  # expired mid-run — nothing to update
    record.update(changes)
    await _write(client, run_id, record)


async def _write(client: redis.Redis, run_id: uuid.UUID, record: dict[str, Any]) -> None:
    await cast(
        "Awaitable[bool]",
        client.set(_key(run_id), json.dumps(record), ex=GUEST_TTL_SECONDS),
    )
