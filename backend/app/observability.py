"""Observability wiring — Logfire + Sentry (design §12, §11).

Everything here is a safe no-op without secrets: Logfire only ships spans when
LOGFIRE_TOKEN is set (`send_to_logfire="if-token-present"`), and Sentry with no DSN is
disabled. So `uv run` and the test suite work unchanged in local dev.

PII protection (§11): Logfire scrubs any attribute whose key looks like PII
(email / jd_text / resume text), and our own structured logs tag user_id (a UUID),
never the email or the resume/JD text. redact_email() is here for the rare case we
must reference a user in a message.
"""

import re

import logfire
import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.integrations.arq import ArqIntegration

from app.config import get_settings

# Attribute keys whose values are PII — Logfire redacts them from every span/log.
_PII_KEY_PATTERNS = [
    "email",
    "jd_text",
    "resume_text",
    "resume_text_snapshot",
    "resume",
]

_configured = False


def configure_observability(service_name: str) -> None:
    """Configure Logfire + Sentry once per process. Called at app and worker startup."""
    global _configured
    if _configured:
        return
    _configured = True

    settings = get_settings()

    logfire.configure(
        service_name=service_name,
        environment=settings.app_env,
        token=settings.logfire_token or None,
        send_to_logfire="if-token-present",  # no token → local no-op, never leaves the box
        console=False,
        inspect_arguments=False,  # we pass explicit kwargs, not f-strings — skip the magic
        scrubbing=logfire.ScrubbingOptions(extra_patterns=_PII_KEY_PATTERNS),
    )
    logfire.instrument_sqlalchemy()
    logfire.instrument_httpx()

    sentry_sdk.init(
        dsn=settings.sentry_dsn or None,  # unset → Sentry disabled (safe no-op)
        environment=settings.app_env,
        integrations=[ArqIntegration()],  # FastAPI/Starlette auto-enable when detected
        traces_sample_rate=0.0,
        send_default_pii=False,
    )


def instrument_app(app: FastAPI) -> None:
    """Trace every request (method, path, status, latency) — no request bodies."""
    logfire.instrument_fastapi(app)


_EMAIL_RE = re.compile(r"([^@\s]+)@([^@\s]+\.[^@\s]+)")


def redact_email(email: str) -> str:
    """Mask an email's local part: 'jane.doe@example.com' -> 'j***@example.com'."""
    match = _EMAIL_RE.fullmatch(email.strip())
    if match is None:
        return "[redacted]"
    local, domain = match.groups()
    return f"{local[0]}***@{domain}"


def scrub_emails(text: str) -> str:
    """Replace any email addresses inside free text with a placeholder."""
    return _EMAIL_RE.sub("[redacted-email]", text)
