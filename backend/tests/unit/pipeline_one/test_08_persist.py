"""Step 08 (persist) — writes the Plan (signed-in) or the Redis record (guest)."""

import importlib
import uuid

import fakeredis.aioredis
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.guest_runs import create_guest_run, read_guest_run
from app.models import Plan, Run, Skill, User, UserSkill
from app.nlp.taxonomy import get_skill_by_id
from app.pipeline_one.state import PipelineState

persist_step = importlib.import_module("app.pipeline_one.08_persist")
persist_logic = importlib.import_module("app.pipeline_one.08_persist.logic")


async def _seed_skills(session, skill_ids) -> None:  # type: ignore[no-untyped-def]
    """Insert real taxonomy skills (idempotent) so user_skills' FK holds."""
    for skill_id in skill_ids:
        skill = get_skill_by_id(skill_id)
        assert skill is not None
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


def _state_for(run_id: uuid.UUID, user_id: uuid.UUID, resume_skill_ids: list[str]) -> PipelineState:
    return PipelineState(
        run_id=run_id,
        user_id=user_id,
        jd_text="jd",
        resume_text="resume",
        resume_skill_ids=resume_skill_ids,
        matched_ids=[],
        missing_ids=[],
        fit_score=0,
        course_a_covered=[],
        course_b_covered=[],
        project_one_md="p1",
        project_two_md="p2",
    )


async def _extracted_and_manual(session, user_id: uuid.UUID):  # type: ignore[no-untyped-def]
    rows = (await session.scalars(select(UserSkill).where(UserSkill.user_id == user_id))).all()
    extracted = {r.skill_id for r in rows if r.source == "extracted"}
    manual = {r.skill_id for r in rows if r.source == "manual"}
    return extracted, manual


async def test_persist_writes_plan_and_completes_run(db_sessionmaker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async with db_sessionmaker() as session:
        user = User(google_sub="persist-test-08", email="p@example.com")
        session.add(user)
        await session.flush()
        run = Run(user_id=user.id, status="running", current_stage=7)
        session.add(run)
        await session.commit()
        user_id, run_id = user.id, run.id

    monkeypatch.setattr(persist_step, "get_sessionmaker", lambda: db_sessionmaker)
    state = PipelineState(
        run_id=run_id,
        user_id=user_id,
        jd_text="a job description",
        resume_text="resume text",
        matched_ids=["python"],
        missing_ids=["docker"],
        fit_score=50,
        course_a_covered=["docker"],
        course_b_covered=[],
        project_one_md="project one",
        project_two_md="project two",
    )

    await persist_step.run(state)

    async with db_sessionmaker() as session:
        run_after = await session.get(Run, run_id)
        assert run_after is not None
        assert run_after.status == "completed"
        assert run_after.current_stage == 8
        assert run_after.completed_at is not None

        plan = (await session.scalars(select(Plan).where(Plan.run_id == run_id))).first()
        assert plan is not None
        assert plan.matched_skill_ids == ["python"]
        assert plan.missing_skill_ids == ["docker"]
        assert plan.fit_score == 50
        assert plan.project_one_md == "project one"

        await session.execute(delete(User).where(User.id == user_id))  # cascades run + plan
        await session.commit()


async def test_persist_merges_extracted_skills_preserving_manual(
    db_sessionmaker, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    async with db_sessionmaker() as session:
        await _seed_skills(session, ["python", "fastapi", "docker", "react"])
        user = User(google_sub="f5-merge", email="m@example.com")
        session.add(user)
        await session.flush()
        run = Run(user_id=user.id, status="running")
        session.add(run)
        # A skill the user added by hand — must survive the merge.
        session.add(UserSkill(user_id=user.id, skill_id="react", source="manual"))
        await session.commit()
        user_id, run_id = user.id, run.id

    monkeypatch.setattr(persist_step, "get_sessionmaker", lambda: db_sessionmaker)
    await persist_step.run(_state_for(run_id, user_id, ["python", "fastapi"]))

    try:
        async with db_sessionmaker() as session:
            extracted, manual = await _extracted_and_manual(session, user_id)
            assert extracted == {"python", "fastapi"}  # the resume's skills
            assert manual == {"react"}  # untouched
    finally:
        await _cleanup_user(db_sessionmaker, user_id)


async def test_reanalysis_replaces_extracted_not_appends(db_sessionmaker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async with db_sessionmaker() as session:
        await _seed_skills(session, ["python", "fastapi", "docker", "react"])
        user = User(google_sub="f5-replace", email="r@example.com")
        session.add(user)
        await session.flush()
        run_one = Run(user_id=user.id, status="running")
        run_two = Run(user_id=user.id, status="running")
        session.add_all([run_one, run_two])
        session.add(UserSkill(user_id=user.id, skill_id="react", source="manual"))
        await session.commit()
        user_id, run_one_id, run_two_id = user.id, run_one.id, run_two.id

    monkeypatch.setattr(persist_step, "get_sessionmaker", lambda: db_sessionmaker)

    try:
        # First analysis: extracted = {python, fastapi}.
        await persist_step.run(_state_for(run_one_id, user_id, ["python", "fastapi"]))
        # Second analysis with a different resume: extracted REPLACED, not appended.
        await persist_step.run(_state_for(run_two_id, user_id, ["python", "docker"]))

        async with db_sessionmaker() as session:
            extracted, manual = await _extracted_and_manual(session, user_id)
            assert extracted == {"python", "docker"}  # fastapi dropped, docker added
            assert manual == {"react"}  # still preserved
    finally:
        await _cleanup_user(db_sessionmaker, user_id)


async def _cleanup_user(db_sessionmaker, user_id) -> None:  # type: ignore[no-untyped-def]
    async with db_sessionmaker() as session:
        await session.execute(delete(User).where(User.id == user_id))  # cascades run + user_skills
        await session.commit()


async def test_guest_persist_writes_the_plan_to_redis_no_db_rows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    run_id = uuid.uuid4()
    await create_guest_run(fake_redis, run_id, "jd")

    monkeypatch.setattr(persist_logic, "get_redis_client", lambda: fake_redis)
    # No courses on this state, so the read-only course lookup does no DB work.
    state = PipelineState(
        run_id=run_id,
        is_guest=True,
        jd_text="jd",
        resume_text="resume",
        matched_ids=["python"],
        missing_ids=["docker"],
        fit_score=50,
        course_a_covered=[],
        course_b_covered=[],
        project_one_md="p1",
        project_two_md="p2",
    )

    await persist_step.run(state)

    record = await read_guest_run(fake_redis, run_id)
    assert record is not None
    assert record["status"] == "completed"
    assert record["current_stage"] == 8
    plan = record["plan"]
    assert plan["fit_score"] == 50
    assert [s["id"] for s in plan["matched_skills"]] == ["python"]
    assert plan["project_one_md"] == "p1"
