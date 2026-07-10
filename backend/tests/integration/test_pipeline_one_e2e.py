"""Pipeline 1 end-to-end: run_pipeline_one over a fixture resume + JD.

Drives the real Arq task through all 8 steps with OpenAI mocked (embeddings + chat)
and R2 faked by moto. Needs Postgres. Asserts the run reaches 'completed' and the
Plan row holds the expected gap / courses / projects, and that a failing step marks
the run 'failed'.
"""

import importlib
import io
import uuid
from collections.abc import AsyncIterator, Iterator

import boto3
import fakeredis.aioredis
import pytest
from docx import Document
from sqlalchemy import NullPool, delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.errors import PipelineStepError
from app.config import get_settings
from app.guest_runs import create_guest_run, read_guest_run
from app.llm.client import ChatResult
from app.models import Course, CourseEmbedding, CourseSkill, Plan, Run, Skill, User, UserSkill
from app.nlp.taxonomy import get_skill_by_id
from app.rag import retriever
from app.storage.r2 import R2Storage
from app.workers import tasks

pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

# The digit-named step/orchestrator modules, loaded by string name.
orchestrator = importlib.import_module("app.pipeline_one")
step01 = importlib.import_module("app.pipeline_one.01_ingest")
step02 = importlib.import_module("app.pipeline_one.02_extract_text")
step07_logic = importlib.import_module("app.pipeline_one.07_generate_projects.logic")
step08_logic = importlib.import_module("app.pipeline_one.08_persist.logic")

QUERY_VECTOR = [1.0] * 1536
RESUME_TEXT = "Experienced Python developer skilled in FastAPI."
JD_TEXT = "We need Python, FastAPI, Docker, and RAG experience."


@pytest.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # DB down / not configured — not a failure
        pytest.skip(f"Postgres not reachable, skipping e2e: {exc}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def moto_r2() -> Iterator[R2Storage]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="e2e-bucket")
        yield R2Storage(client, "e2e-bucket")


def make_docx(text_content: str) -> bytes:
    buffer = io.BytesIO()
    document = Document()
    document.add_paragraph(text_content)
    document.save(buffer)
    return buffer.getvalue()


def use_test_db(monkeypatch, maker) -> None:  # type: ignore[no-untyped-def]
    """Point the orchestrator, DB-backed steps, and the task at the test sessionmaker."""
    for module in (orchestrator, tasks):
        monkeypatch.setattr(module, "get_sessionmaker", lambda: maker)
    for name in ("05_retrieve_courses", "06_select_courses", "08_persist"):
        step = importlib.import_module(f"app.pipeline_one.{name}")
        monkeypatch.setattr(step, "get_sessionmaker", lambda: maker)


async def _make_user_and_run(maker) -> tuple[uuid.UUID, uuid.UUID]:  # type: ignore[no-untyped-def]
    async with maker() as session:
        user = User(google_sub=f"e2e-{uuid.uuid4()}", email="e2e@example.com")
        session.add(user)
        await session.flush()
        run = Run(user_id=user.id, status="queued")
        session.add(run)
        await session.commit()
        return user.id, run.id


async def _seed_course(maker, external_id: str, skills: set[str]) -> uuid.UUID:  # type: ignore[no-untyped-def]
    async with maker() as session:
        course = Course(
            platform="test", external_id=external_id, title=external_id, url="https://x/c"
        )
        session.add(course)
        await session.flush()
        for skill_id in skills:
            session.add(CourseSkill(course_id=course.id, skill_id=skill_id))
        session.add(CourseEmbedding(course_id=course.id, embedding=QUERY_VECTOR))
        await session.commit()
        return course.id


async def _seed_skill(maker, skill_id: str) -> None:  # type: ignore[no-untyped-def]
    skill = get_skill_by_id(skill_id)
    assert skill is not None
    async with maker() as session:
        await session.execute(
            pg_insert(Skill)
            .values(
                id=skill.id,
                display_name=skill.canonical_name,
                category=skill.category,
                priority_rank=skill.priority_rank,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.commit()


async def test_full_run_completes_and_writes_a_plan(sessionmaker_, moto_r2, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id, run_id = await _make_user_and_run(sessionmaker_)
    course_a = await _seed_course(sessionmaker_, "e2e-a", {"docker", "rag"})  # score 2+1
    course_b = await _seed_course(sessionmaker_, "e2e-b", {"docker"})  # score 2
    # The resume's extracted skills need skills rows for the F5 merge's FK.
    await _seed_skill(sessionmaker_, "python")
    await _seed_skill(sessionmaker_, "fastapi")

    use_test_db(monkeypatch, sessionmaker_)
    monkeypatch.setattr(step01, "get_r2", lambda: moto_r2)
    monkeypatch.setattr(step02, "get_r2", lambda: moto_r2)

    async def fake_embed(_text: str) -> list[float]:
        return QUERY_VECTOR

    monkeypatch.setattr(retriever, "embed_text", fake_embed)

    async def fake_chat(messages, *, model, temperature=0.7, max_tokens=None, run_id=None):  # type: ignore[no-untyped-def]
        is_skillbridge = "BOTH sets together" in messages[0]["content"]
        return ChatResult(
            text="skillbridge" if is_skillbridge else "fast-apply",
            model=model,
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=0.0,
        )

    monkeypatch.setattr(step07_logic, "chat", fake_chat)

    try:
        await tasks.run_pipeline_one(
            {}, str(run_id), make_docx(RESUME_TEXT), JD_TEXT, "resume.docx"
        )

        async with sessionmaker_() as session:
            run = await session.get(Run, run_id)
            assert run is not None
            assert run.status == "completed"
            assert run.current_stage == 8

            plan = (await session.scalars(select(Plan).where(Plan.run_id == run_id))).first()
            assert plan is not None
            assert plan.matched_skill_ids == ["fastapi", "python"]
            assert plan.missing_skill_ids == ["docker", "rag"]  # priority-sorted
            assert plan.fit_score == 50  # round(100 * 2/4)
            assert plan.course_a_id == course_a and plan.course_b_id == course_b
            assert plan.course_a_covered == ["docker", "rag"]
            assert plan.course_b_covered == ["docker"]
            assert plan.project_one_md == "fast-apply"
            assert plan.project_two_md == "skillbridge"

            # F5: the resume's extracted skills were merged into the dashboard.
            extracted = (
                await session.scalars(
                    select(UserSkill.skill_id).where(
                        UserSkill.user_id == user_id, UserSkill.source == "extracted"
                    )
                )
            ).all()
            assert set(extracted) == {"fastapi", "python"}
    finally:
        await _cleanup(sessionmaker_, user_id, [course_a, course_b])


async def test_failing_step_marks_the_run_failed(sessionmaker_, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id, run_id = await _make_user_and_run(sessionmaker_)
    use_test_db(monkeypatch, sessionmaker_)

    async def failing_run(_state):  # type: ignore[no-untyped-def]
        raise PipelineStepError("we couldn't read this file — try re-saving as PDF")

    monkeypatch.setattr(step01, "run", failing_run)

    try:
        await tasks.run_pipeline_one({}, str(run_id), b"irrelevant", JD_TEXT, "resume.pdf")

        async with sessionmaker_() as session:
            run = await session.get(Run, run_id)
            assert run is not None
            assert run.status == "failed"
            assert "couldn't read this file" in (run.error_message or "")
    finally:
        await _cleanup(sessionmaker_, user_id, [])


def _mock_openai_and_r2(monkeypatch, moto_r2) -> None:  # type: ignore[no-untyped-def]
    """Shared mocks: R2 (steps 01/02), embeddings (retrieve), chat (generate)."""
    monkeypatch.setattr(step01, "get_r2", lambda: moto_r2)
    monkeypatch.setattr(step02, "get_r2", lambda: moto_r2)

    async def fake_embed(_text: str) -> list[float]:
        return QUERY_VECTOR

    monkeypatch.setattr(retriever, "embed_text", fake_embed)

    async def fake_chat(messages, *, model, temperature=0.7, max_tokens=None, run_id=None):  # type: ignore[no-untyped-def]
        is_skillbridge = "BOTH sets together" in messages[0]["content"]
        return ChatResult(
            text="skillbridge" if is_skillbridge else "fast-apply",
            model=model,
            prompt_tokens=10,
            completion_tokens=20,
            cost_usd=0.0,
        )

    monkeypatch.setattr(step07_logic, "chat", fake_chat)


async def test_guest_run_completes_in_redis_with_zero_db_writes(
    sessionmaker_, moto_r2, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    course_a = await _seed_course(sessionmaker_, "guest-a", {"docker", "rag"})
    course_b = await _seed_course(sessionmaker_, "guest-b", {"docker"})

    use_test_db(monkeypatch, sessionmaker_)  # reads (retrieve/select/course lookup)
    _mock_openai_and_r2(monkeypatch, moto_r2)

    # A guest has no DB rows — just a Redis record. The pipeline reaches Redis via
    # get_redis_client() in the orchestrator (stage bumps) and step 08 (the plan).
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(orchestrator, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(step08_logic, "get_redis_client", lambda: fake_redis)

    run_id = uuid.uuid4()
    await create_guest_run(fake_redis, run_id, JD_TEXT)

    try:
        await tasks.run_pipeline_one(
            {}, str(run_id), make_docx(RESUME_TEXT), JD_TEXT, "resume.docx", True
        )

        record = await read_guest_run(fake_redis, run_id)
        assert record is not None
        assert record["status"] == "completed"
        assert record["current_stage"] == 8

        plan = record["plan"]
        assert plan is not None
        assert [s["id"] for s in plan["matched_skills"]] == ["fastapi", "python"]
        assert [s["id"] for s in plan["missing_skills"]] == ["docker", "rag"]
        assert plan["fit_score"] == 50
        assert plan["project_one_md"] == "fast-apply"
        assert plan["project_two_md"] == "skillbridge"
        assert {c["course_id"] for c in plan["courses"]} == {str(course_a), str(course_b)}

        # ZERO DB writes for the guest: no run or plan rows exist for this run_id.
        async with sessionmaker_() as session:
            assert await session.get(Run, run_id) is None
            leftover = (await session.scalars(select(Plan).where(Plan.run_id == run_id))).first()
            assert leftover is None
    finally:
        async with sessionmaker_() as session:
            await session.execute(delete(Course).where(Course.id.in_([course_a, course_b])))
            await session.commit()


async def _cleanup(maker, user_id, course_ids) -> None:  # type: ignore[no-untyped-def]
    async with maker() as session:
        await session.execute(delete(User).where(User.id == user_id))  # cascades run + plan
        if course_ids:
            await session.execute(delete(Course).where(Course.id.in_(course_ids)))
        await session.commit()
