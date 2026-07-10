"""FastAPI application entry point.

Wires the app together: the health check, the SessionMiddleware that holds the
short-lived OAuth transaction state, and the route routers. Business logic lives in
the modules the routers call, not here.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import analyze, auth, dashboard, health, jobs, plans
from app.common.rate_limit import RateLimitExceeded
from app.config import get_settings
from app.observability import configure_observability, instrument_app


def _rate_limit_handler(_request: Request, exc: Exception) -> JSONResponse:
    retry_after = exc.retry_after if isinstance(exc, RateLimitExceeded) else 60
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limited", "detail": "Too many requests. Please try again later."},
        headers={"Retry-After": str(retry_after)},
    )


def create_app() -> FastAPI:
    configure_observability("skillbridge-api")  # Logfire + Sentry (no-op without secrets)
    app = FastAPI(title="SkillBridge Backend")
    settings = get_settings()

    # Let the frontend send its session cookie on cross-origin requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # Holds only the OAuth state/nonce/PKCE verifier between login and callback.
    # The real app session is server-side and Redis-backed (app/auth/sessions.py).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=settings.cookie_secure,
    )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(analyze.router)
    app.include_router(plans.router)
    app.include_router(jobs.router)
    app.include_router(health.router)

    instrument_app(app)  # trace requests via Logfire (no-op without a token)
    return app


app = create_app()
