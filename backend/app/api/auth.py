"""Auth routes — HTTP only. All OAuth and session logic lives in app/auth/.

Flow: /auth/google/login sends the user to Google; /auth/google/callback brings
them back with a code, which we exchange for verified claims, upsert into a user,
and turn into a Redis-backed session carried by an HttpOnly cookie.
"""

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import google
from app.auth.sessions import create_session, revoke_session
from app.common.csrf import clear_csrf_cookie, set_csrf_cookie
from app.common.rate_limit import limit_auth_endpoints
from app.config import get_settings
from app.deps import get_current_user, get_db, get_redis
from app.models import User
from app.schemas.auth import MeResponse

router = APIRouter(tags=["auth"])

# Where the user lands after a successful sign-in.
POST_LOGIN_REDIRECT = "/analyze"


@router.get("/auth/google/login", dependencies=[Depends(limit_auth_endpoints)])
async def google_login(request: Request) -> RedirectResponse:
    return await google.build_login_redirect(request)


@router.get("/auth/google/callback", dependencies=[Depends(limit_auth_endpoints)])
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: redis.Redis = Depends(get_redis),
) -> RedirectResponse:
    claims = await google.fetch_verified_claims(request)
    user = await google.upsert_user(db, claims)

    settings = get_settings()
    session_id = await create_session(client, user.id, settings.session_ttl_seconds)

    response = RedirectResponse(POST_LOGIN_REDIRECT, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, session_id)
    set_csrf_cookie(response)  # readable token for double-submit on authed writes
    return response


@router.post("/auth/google/logout")
async def google_logout(
    request: Request,
    client: redis.Redis = Depends(get_redis),
) -> Response:
    session_id = request.cookies.get(get_settings().session_cookie_name)
    if session_id:
        await revoke_session(client, session_id)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    clear_csrf_cookie(response)
    return response


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
