# Live image for both Railway services (web + worker) — same image, different start
# command. Deliberately lean: no Playwright/browser binaries (scrapers are offline,
# §7), no tests, no dev deps.

FROM python:3.12-slim

# The one system dependency the runtime needs: libmagic for python-magic's magic-byte
# file-type check (step 01). pypdf / python-docx / boto3 are pure Python.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, reproducible installs (pinned via uv.lock).
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Install runtime deps first, as their own cached layer (only the lockfile changes it).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# App code + the JSON data the runtime reads (taxonomy, companies) + migrations.
# NOT scrapers/, tests/, or the scrapers' HTML dumps.
COPY app ./app
COPY data ./data
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000
# Default (web). Railway's worker service overrides this with the arq start command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
