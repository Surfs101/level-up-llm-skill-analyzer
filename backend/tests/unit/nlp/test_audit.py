"""Tests for app/nlp/audit.py — the drift-detection CLI.

Feeds two synthetic files through scan_directory (the pure, no-write core) and
checks the report shape, that a planted skill-shaped-but-unknown token surfaces
as a candidate gap, and that a real (matched) skill never does.
"""

from pathlib import Path

from app.nlp import audit


def write_files(directory: Path) -> None:
    (directory / "resume_one.txt").write_text(
        "Backend engineer working in Python and PostgreSQL. "
        "Also shipped a service in FooLangXYZ last year."
    )
    (directory / "resume_two.txt").write_text(
        "We use Python heavily. The data layer is built on FooLangXYZ with a PostgreSQL warehouse."
    )


def test_report_shape(tmp_path: Path) -> None:
    write_files(tmp_path)
    report = audit.scan_directory(tmp_path, min_files=2)

    assert set(report) == {
        "scanned_files",
        "total_matches",
        "matches_by_category",
        "candidate_gaps",
    }
    assert report["scanned_files"] == 2
    assert report["total_matches"] > 0
    # Python is a language, PostgreSQL a database — both matched in both files.
    assert report["matches_by_category"]["language"] >= 1
    assert report["matches_by_category"]["database"] >= 1


def test_planted_unknown_token_is_flagged(tmp_path: Path) -> None:
    write_files(tmp_path)
    report = audit.scan_directory(tmp_path, min_files=2)

    gaps_by_token = {gap["token"]: gap for gap in report["candidate_gaps"]}
    assert "FooLangXYZ" in gaps_by_token
    planted = gaps_by_token["FooLangXYZ"]
    assert planted["occurrences"] == 2
    assert planted["files"] == ["resume_one.txt", "resume_two.txt"]


def test_real_skills_are_not_flagged(tmp_path: Path) -> None:
    write_files(tmp_path)
    report = audit.scan_directory(tmp_path, min_files=2)

    flagged_tokens = {gap["token"] for gap in report["candidate_gaps"]}
    # PostgreSQL is CamelCase-shaped but it MATCHED, so it must not be a gap.
    assert "PostgreSQL" not in flagged_tokens
    assert "Python" not in flagged_tokens


def test_min_files_threshold(tmp_path: Path) -> None:
    # A token in only one file is below the default threshold of 2.
    (tmp_path / "only.txt").write_text("A prototype in SoloLangABC nobody else uses.")
    report = audit.scan_directory(tmp_path, min_files=2)
    assert report["candidate_gaps"] == []

    # Lowering the threshold to 1 surfaces it.
    report_loose = audit.scan_directory(tmp_path, min_files=1)
    assert any(gap["token"] == "SoloLangABC" for gap in report_loose["candidate_gaps"])


def test_empty_directory_is_graceful(tmp_path: Path) -> None:
    report = audit.scan_directory(tmp_path, min_files=2)
    assert report["scanned_files"] == 0
    assert report["total_matches"] == 0
    assert report["matches_by_category"] == {}
    assert report["candidate_gaps"] == []
