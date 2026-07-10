"""CSRF double-submit token for non-idempotent authed writes (design §11).

Defense-in-depth on top of the SameSite=Lax session cookie (which browsers already
withhold on cross-site non-GET requests). It's stateless: a random token is set in a
*readable* (non-HttpOnly) cookie at sign-in; the frontend echoes it in the
X-CSRF-Token header on writes; the server checks the two match. A cross-site attacker
can't read the victim's cookie (it's on our domain) so can't forge the header.
"""

import secrets

from fastapi import HTTPException, Request, Response, status

from app.config import get_settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def set_csrf_cookie(response: Response) -> None:
    settings = get_settings()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        max_age=settings.session_ttl_seconds,
        httponly=False,  # the frontend must read it to echo in the header
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def clear_csrf_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


async def require_csrf(request: Request) -> None:
    """Route dependency: reject if the CSRF cookie and header are missing or unequal."""
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get(CSRF_HEADER_NAME)
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid or missing CSRF token")
