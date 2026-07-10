"""Step 03 logic — job content -> canonical skill ids (design §9 step 3).

Strips the HTML from each posting, then runs the SAME matcher Pipeline 1 uses
(app/nlp/matcher.py). That shared extractor is the whole point: a resume, a JD, and a
job posting are all reduced to the same id space, so the `/jobs` overlap score is
meaningful. A posting that mentions no known skill gets an empty list — it's still a
real posting and is stored (step 04) with no job_skills rows.
"""

from app.common.html import strip_html
from app.greenhouse.client import GreenhousePosting
from app.nlp.matcher import extract_skill_ids

from .schemas import ExtractResult


def job_key(posting: GreenhousePosting) -> str:
    """The stable per-posting key: (company, gh_job_id) is unique."""
    return f"{posting.company}/{posting.gh_job_id}"


def extract(postings: list[GreenhousePosting]) -> ExtractResult:
    skills_by_job = {
        job_key(posting): sorted(extract_skill_ids(strip_html(posting.content)))
        for posting in postings
    }
    return ExtractResult(skills_by_job=skills_by_job)
