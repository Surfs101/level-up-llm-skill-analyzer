"""The Phase-4 models import and register on the shared metadata."""

from app.models import Base, Plan, Resume, Run


def test_new_models_are_registered() -> None:
    assert Resume.__tablename__ == "resumes"
    assert Run.__tablename__ == "runs"
    assert Plan.__tablename__ == "plans"
    for table in ("resumes", "runs", "plans"):
        assert table in Base.metadata.tables
