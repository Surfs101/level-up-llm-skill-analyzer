"""Pytest configuration.

Adds the backend root (this file's grandparent) to sys.path so tests can import
app, scripts, and scrapers regardless of how pytest is invoked.
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _configure_observability() -> None:
    """Configure Logfire/Sentry once (a no-op without secrets), like app/worker startup.

    Tests that call the pipeline directly bypass create_app(), so without this the
    orchestrator's logfire spans would warn 'not configured'.
    """
    from app.observability import configure_observability

    configure_observability("skillbridge-test")
