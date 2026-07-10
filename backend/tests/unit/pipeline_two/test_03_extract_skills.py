"""Step 03 (extract skills) — HTML strip + the shared matcher; empty is not an error."""

import importlib

extract_logic = importlib.import_module("app.pipeline_two.03_extract_skills.logic")


def test_extracts_skills_from_html_content(make_posting) -> None:  # type: ignore[no-untyped-def]
    posting = make_posting(
        company="test-acme",
        gh_job_id="1",
        content="<div>We use <b>Python</b> and FastAPI &amp; Docker.</div>",
    )

    result = extract_logic.extract([posting])

    covered = set(result.skills_by_job["test-acme/1"])
    assert {"python", "fastapi", "docker"} <= covered


def test_posting_with_no_known_skills_gets_empty_list(make_posting) -> None:  # type: ignore[no-untyped-def]
    posting = make_posting(
        company="test-acme", gh_job_id="2", content="<p>The quick brown fox.</p>"
    )

    result = extract_logic.extract([posting])

    # Not an error — the posting is still stored, just with no skills.
    assert result.skills_by_job["test-acme/2"] == []
