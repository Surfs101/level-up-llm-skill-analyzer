"""Google OAuth sign-in via Authlib (OpenID Connect).

We register Google by its OIDC discovery document, so Authlib pulls the authorize
endpoint, token endpoint, and JWKS itself. That means `authorize_access_token`
does the security-critical work for us: it exchanges the code, then validates the
returned ID token's signature against Google's JWKS and checks `aud` (our client
id), `iss`, `exp`, and the `nonce`. We deliberately do NOT hand-roll JWT/JWKS
verification — this is exactly the kind of crypto a well-maintained library should
own.

PKCE is enabled via `code_challenge_method=S256`. The short-lived OAuth transaction
state (state, nonce, PKCE verifier) is held by Starlette's SessionMiddleware; the
long-lived app session is separate (app/auth/sessions.py).
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import cast

from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.models import User

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


@dataclass(frozen=True)
class GoogleClaims:
    """The identity fields we keep from a verified Google ID token."""

    google_sub: str
    email: str
    name: str | None
    avatar_url: str | None


@lru_cache(maxsize=1)
def get_oauth() -> OAuth:
    """Build (once) the Authlib OAuth registry with Google configured."""
    settings = get_settings()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
    )
    return oauth


async def build_login_redirect(request: Request) -> RedirectResponse:
    """Start the flow: redirect the user to Google's consent screen (with PKCE)."""
    redirect_uri = get_settings().oauth_redirect_uri
    # Authlib is untyped, so cast its return to the RedirectResponse it actually is.
    response = await get_oauth().google.authorize_redirect(request, redirect_uri)
    return cast(RedirectResponse, response)


async def fetch_verified_claims(request: Request) -> GoogleClaims:
    """Complete the callback: exchange the code and return verified identity claims.

    Raises if the code is bad or the ID token fails validation — the caller turns
    that into a failed sign-in.
    """
    token = await get_oauth().google.authorize_access_token(request)
    claims = token["userinfo"]  # already signature/aud/iss/nonce-validated by Authlib
    return GoogleClaims(
        google_sub=claims["sub"],
        email=claims.get("email", ""),
        name=claims.get("name"),
        avatar_url=claims.get("picture"),
    )


async def upsert_user(db: AsyncSession, claims: GoogleClaims) -> User:
    """Find the user by google_sub and refresh their profile, or create them."""
    user = await db.scalar(select(User).where(User.google_sub == claims.google_sub))
    if user is None:
        user = User(
            google_sub=claims.google_sub,
            email=claims.email,
            name=claims.name,
            avatar_url=claims.avatar_url,
        )
        db.add(user)
    else:
        # Keep the profile fresh; leave deleted_at untouched (account lifecycle is
        # owned by the delete flow, not sign-in).
        user.email = claims.email
        user.name = claims.name
        user.avatar_url = claims.avatar_url
    await db.commit()
    await db.refresh(user)
    return user
