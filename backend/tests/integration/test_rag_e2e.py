"""End-to-end RAG test: gap -> retrieve -> rank -> select, against the live corpus.

Needs Postgres (the seeded course_embeddings) AND OpenAI (to embed the gap), so it
skips cleanly when either is unavailable — CI has neither yet.

The corpus is GenAI/LLM-weighted, so an in-corpus gap returns sensible picks and an
out-of-corpus gap (rust/kubernetes/terraform) returns nothing — that's the narrow
corpus degrading gracefully, not a bug.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.llm.embeddings import embed_text
from app.rag.ranker import select_courses
from app.rag.retriever import retrieve_candidates

IN_CORPUS_GAP = ["large-language-models", "rag", "vector-search"]
OUT_OF_CORPUS_GAP = ["rust", "kubernetes", "terraform"]


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """A DB session, but skip if Postgres or OpenAI isn't reachable."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await embed_text("connectivity check")  # confirm OpenAI is usable too
    except Exception as exc:  # missing config / DB down / no API key — not a failure
        pytest.skip(f"DB or OpenAI not available: {exc}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as open_session:
        yield open_session
    await engine.dispose()


async def test_in_corpus_gap_returns_two_sensible_courses(session: AsyncSession) -> None:
    candidates = await retrieve_candidates(session, IN_CORPUS_GAP)
    assert candidates, "retrieval returned no candidates"

    course_a, course_b = select_courses(candidates, IN_CORPUS_GAP)
    assert course_a is not None and course_b is not None

    gap = set(IN_CORPUS_GAP)
    for pick in (course_a, course_b):
        assert pick.covered, "a selected course must cover at least one gap skill"
        assert pick.covered <= gap, "covered skills must be a subset of the gap"
    assert course_a.score >= course_b.score, "Course A must rank at least as high as B"


async def test_in_corpus_selection_is_deterministic(session: AsyncSession) -> None:
    first = select_courses(await retrieve_candidates(session, IN_CORPUS_GAP), IN_CORPUS_GAP)
    second = select_courses(await retrieve_candidates(session, IN_CORPUS_GAP), IN_CORPUS_GAP)
    assert first[0] is not None and second[0] is not None
    assert first[0].course.id == second[0].course.id
    assert first[1] is not None and second[1] is not None
    assert first[1].course.id == second[1].course.id


async def test_out_of_corpus_gap_degrades_gracefully(session: AsyncSession) -> None:
    # Retrieval still returns the nearest courses, but none cover rust/k8s/terraform,
    # so the ranker yields no picks instead of recommending something irrelevant.
    candidates = await retrieve_candidates(session, OUT_OF_CORPUS_GAP)
    course_a, course_b = select_courses(candidates, OUT_OF_CORPUS_GAP)
    assert course_a is None and course_b is None
