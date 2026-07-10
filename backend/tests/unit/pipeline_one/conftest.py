"""Shared fixtures for the Pipeline 1 step tests.

Builders for real (tiny) PDF/DOCX bytes and a moto-backed R2Storage (steps 01–02),
plus a Postgres session factory and a course seeder (steps 05–06). Steps 03–04 are
pure and need none of this.
"""

import io
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from decimal import Decimal

import boto3
import pytest
from docx import Document
from sqlalchemy import NullPool, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Course, CourseEmbedding, CourseSkill

pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

from app.storage.r2 import R2Storage  # noqa: E402


@pytest.fixture
def make_pdf() -> Callable[[str], bytes]:
    """Build a minimal, valid, text-bearing PDF (correct xref so pypdf reads it)."""

    def _make(text: str) -> bytes:
        objects = [
            b"<</Type/Catalog/Pages 2 0 R>>",
            b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
            b"/Resources<</Font<</F1 5 0 R>>>>>>",
        ]
        stream = b"BT /F1 24 Tf 72 700 Td (" + text.encode("latin-1") + b") Tj ET"
        objects.append(
            b"<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream"
        )
        objects.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
        xref_pos = len(out)
        out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode()
        out += b"trailer<</Size " + str(len(objects) + 1).encode() + b"/Root 1 0 R>>\n"
        out += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
        return bytes(out)

    return _make


@pytest.fixture
def make_docx() -> Callable[[str], bytes]:
    """Build a real .docx containing the given text."""

    def _make(text: str) -> bytes:
        buffer = io.BytesIO()
        document = Document()
        document.add_paragraph(text)
        document.save(buffer)
        return buffer.getvalue()

    return _make


@pytest.fixture
def r2() -> Iterator[R2Storage]:
    """An R2Storage backed by an in-process S3 (moto), bound to a fresh bucket."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        yield R2Storage(client, "test-bucket")


@pytest.fixture
async def db_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A NullPool session factory, or skip if Postgres isn't reachable."""
    try:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # missing config or unreachable DB — not a failure
        pytest.skip(f"Postgres not reachable, skipping DB test: {exc}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def course_seeder(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[Callable[..., object]]:
    """Insert throwaway courses (with skills, optional duration/embedding) and clean
    them all up at teardown. Returns their generated ids."""
    created: list[uuid.UUID] = []

    async def _seed(
        external_id: str,
        skill_ids: set[str],
        duration: Decimal | None = None,
        embedding: list[float] | None = None,
    ) -> uuid.UUID:
        async with db_sessionmaker() as session:
            course = Course(
                platform="test",
                external_id=external_id,
                title=external_id,
                url="https://example.com/course",
                duration_hours=duration,
            )
            session.add(course)
            await session.flush()
            for skill_id in skill_ids:
                session.add(CourseSkill(course_id=course.id, skill_id=skill_id))
            if embedding is not None:
                session.add(CourseEmbedding(course_id=course.id, embedding=embedding))
            await session.commit()
            created.append(course.id)
            return course.id

    yield _seed

    async with db_sessionmaker() as session:
        await session.execute(delete(Course).where(Course.id.in_(created)))
        await session.commit()
