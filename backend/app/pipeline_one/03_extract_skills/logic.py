"""Step 03 logic — resume + JD text -> canonical skill ids (design §8 step 3).

This step does not do any matching of its own: it delegates to the one shared
matcher (app/nlp/matcher.py) for both texts, so resumes, JDs, and (in Pipeline 2)
job posts are all reduced to the exact same id space. The ids are sorted so the
state is deterministic; the sets are turned into lists to live on the state.
"""

from app.nlp.matcher import extract_skill_ids

from .schemas import ExtractSkillsResult


def extract_skills(resume_text: str, jd_text: str) -> ExtractSkillsResult:
    return ExtractSkillsResult(
        resume_skill_ids=sorted(extract_skill_ids(resume_text)),
        jd_skill_ids=sorted(extract_skill_ids(jd_text)),
    )
