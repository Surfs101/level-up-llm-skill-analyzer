"""Analyze routes — trigger a run and poll it. HTTP only.

POST /analyze starts an analysis; GET /runs/{id} polls it. Both serve signed-in users
AND guests. A signed-in run gets Resume + Run rows in Postgres and (eventually) a Plan;
a guest run has NO DB rows — it lives only in a Redis record with a 1-hour TTL, and its
plan comes back inline from GET /runs (design §10, F3).

Per-user rate limiting and the guest 5×/24h cap are separate Phase-6 items.
"""

import hashlib
import uuid

import redis.asyncio as redis
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.rate_limit import (
    GUEST_ANALYZE_LIMIT,
    USER_ANALYZE_LIMIT,
    enforce,
    hashed_ip,
)
from app.deps import get_current_user_optional, get_db, get_redis
from app.guest_runs import create_guest_run, read_guest_run
from app.models import Plan, Resume, Run, User
from app.schemas.analyze import AnalyzeResponse, RunStatusResponse
from app.workers.queue import get_arq_pool

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze(
    request: Request,
    jd_text: str = Form(...),
    resume: UploadFile = File(...),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
    queue: ArqRedis = Depends(get_arq_pool),
) -> AnalyzeResponse:
    file_bytes = await resume.read()

    if user is None:
        # Guest: 5 per 24h per IP (§10). No DB rows — just a Redis record with a TTL.
        await enforce(client, f"rl:guest:{hashed_ip(request)}", GUEST_ANALYZE_LIMIT)
        run_id = uuid.uuid4()
        await create_guest_run(client, run_id, jd_text)
        await queue.enqueue_job(
            "run_pipeline_one", str(run_id), file_bytes, jd_text, resume.filename, True
        )
        return AnalyzeResponse(run_id=run_id)

    # Signed-in: 20 per day per user (§11), then Resume + Run rows. The .txt key is
    # content-addressed, so we know it now even though step 02 writes the object later.
    # The upload is validated in step 01.
    await enforce(client, f"rl:user:{user.id}", USER_ANALYZE_LIMIT)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    resume_row = Resume(
        user_id=user.id,
        r2_key_text=f"resumes/{file_hash}.txt",
        file_hash=file_hash,
        filename=resume.filename,
    )
    db.add(resume_row)
    await db.flush()
    run = Run(user_id=user.id, resume_id=resume_row.id, status="queued")
    db.add(run)
    await db.commit()

    await queue.enqueue_job("run_pipeline_one", str(run.id), file_bytes, jd_text, resume.filename)
    return AnalyzeResponse(run_id=run.id)


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(
    run_id: uuid.UUID,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
) -> RunStatusResponse:
    # A signed-in user's own run lives in Postgres.
    if user is not None:
        run = await db.get(Run, run_id)
        if run is not None and run.user_id == user.id:
            plan_id = None
            if run.status == "completed":
                plan_id = await db.scalar(select(Plan.id).where(Plan.run_id == run.id))
            return RunStatusResponse.from_run(run, plan_id=plan_id)

    # Otherwise it may be a guest run in Redis (or an expired/unknown id → 404).
    record = await read_guest_run(client, run_id)
    if record is not None:
        return RunStatusResponse.from_guest(run_id, record)

    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Run not found")
