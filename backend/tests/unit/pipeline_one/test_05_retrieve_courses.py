"""Step 05 (retrieve courses) — pgvector retrieval over a seeded DB.

Needs Postgres (skip-if-no-DB). The embedding call is monkeypatched so no OpenAI is
needed: seeded courses share the exact query vector, so they're the nearest matches
and land in the top-50.
"""

import importlib
import uuid

from app.pipeline_one.state import PipelineState
from app.rag import retriever

retrieve_step = importlib.import_module("app.pipeline_one.05_retrieve_courses")

QUERY_VECTOR = [1.0] * 1536


async def test_retrieve_stores_candidate_ids(course_seeder, db_sessionmaker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    course_a = await course_seeder("test-step5-a", {"python"}, embedding=QUERY_VECTOR)
    course_b = await course_seeder("test-step5-b", {"fastapi"}, embedding=QUERY_VECTOR)

    async def fake_embed(_text: str) -> list[float]:
        return QUERY_VECTOR

    monkeypatch.setattr(retriever, "embed_text", fake_embed)
    monkeypatch.setattr(retrieve_step, "get_sessionmaker", lambda: db_sessionmaker)

    state = PipelineState(run_id=uuid.uuid4(), jd_text="jd", missing_ids=["python", "fastapi"])
    result = await retrieve_step.run(state)

    ids = set(result.retrieved_course_ids)
    assert course_a in ids and course_b in ids  # distance 0 -> guaranteed in top-50
    assert len(result.retrieved_course_ids) <= 50
