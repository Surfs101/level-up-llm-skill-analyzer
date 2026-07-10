"""Application configuration, read from the environment (a local .env in dev).

Nothing here connects to anything — instantiating Settings only reads values.
Call get_settings() to obtain the single cached instance.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # Infrastructure
    database_url: str
    redis_url: str

    # OpenAI
    openai_api_key: str

    # Cloudflare R2 (S3-compatible object storage)
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    # Storage endpoint override. Empty in production, where the endpoint is derived from
    # r2_account_id (Cloudflare R2). For local dev, set this to the MinIO URL
    # (http://localhost:9000) to use MinIO — a free, offline, S3-compatible R2 stand-in.
    r2_endpoint_url: str = ""

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    # Where Google sends the user back after consent. Must be allowlisted in the
    # Google Cloud console. Defaults to the local callback for dev.
    oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Server-side session cookie signing (used by Starlette's SessionMiddleware,
    # which holds the short-lived OAuth transaction state — not the app session).
    session_secret: str

    # App session cookie (server-side, Redis-backed — see app/auth/sessions.py).
    session_cookie_name: str = "sid"
    session_ttl_seconds: int = 604800  # 7 days
    # Secure cookies require HTTPS. False for local http dev; True in production.
    cookie_secure: bool = False
    # SameSite for the app cookies (sid + csrf). The Vercel frontend is a DIFFERENT
    # origin than the Railway API, so cross-site fetch needs "none" in prod — which
    # browsers only accept alongside Secure. Local dev (same-origin-ish) uses "lax".
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # The frontend origin allowed to make credentialed (cookie) requests. In prod
    # this is the Vercel URL. Credentialed CORS can't use "*", so it's explicit.
    frontend_origin: str = "http://localhost:3000"

    # Observability — optional in local dev, so they default to empty.
    sentry_dsn: str = ""
    logfire_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
