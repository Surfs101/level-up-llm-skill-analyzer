"""Health routes (design §12). Routes only — the checks live in app/health.py.

/healthz is liveness: 200 iff Postgres + Redis are reachable, 503 otherwise.
/readyz is readiness: /healthz plus the taxonomy being loaded and OpenAI authenticating.
"""

from fastapi import APIRouter, Response, status

from app.health import check_openai, check_postgres, check_redis, check_taxonomy

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(response: Response) -> dict[str, bool | str]:
    postgres = await check_postgres()
    redis = await check_redis()
    healthy = postgres and redis
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "unhealthy", "postgres": postgres, "redis": redis}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, bool | str]:
    postgres = await check_postgres()
    redis = await check_redis()
    taxonomy = check_taxonomy()
    openai = await check_openai()
    ready = postgres and redis and taxonomy and openai
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "postgres": postgres,
        "redis": redis,
        "taxonomy": taxonomy,
        "openai": openai,
    }
