"""Step 04 logic — compare the two skill sets and score the fit (design §8 step 4).

matched = resume ∩ jd, missing = jd − resume. Missing skills are sorted by
priority_rank ascending (languages first, techniques last) so the UI shows the most
foundational gaps first; ties break on id for determinism. fit_score is the share of
the JD's skills the resume already covers.
"""

from app.common.errors import PipelineStepError
from app.nlp.taxonomy import get_priority_rank

from .schemas import GapResult

# Either side being empty means a junk upload or a soft-skills-only JD — and an empty
# JD set would also divide by zero below.
NO_SKILLS = (
    "we couldn't find technical skills — make sure the resume and the job "
    "description list the actual tech stack."
)


def analyze_gap(resume_skill_ids: list[str], jd_skill_ids: list[str]) -> GapResult:
    resume = set(resume_skill_ids)
    jd = set(jd_skill_ids)
    if not resume or not jd:
        raise PipelineStepError(NO_SKILLS)

    matched = resume & jd
    missing = jd - resume
    missing_sorted = sorted(missing, key=lambda skill_id: (get_priority_rank(skill_id), skill_id))
    fit_score = round(100 * len(matched) / len(jd))

    return GapResult(matched_ids=sorted(matched), missing_ids=missing_sorted, fit_score=fit_score)
