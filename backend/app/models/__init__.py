"""ORM models.

Importing the models here registers them on Base.metadata, which is what Alembic
autogenerate reads. Any new model must be imported here too, or migrations will
silently miss it.
"""

from app.models.base import Base
from app.models.course import Course, CourseEmbedding, CourseSkill
from app.models.job_posting import JobPosting, JobSkill
from app.models.llm_call import LlmCall
from app.models.plan import Plan
from app.models.resume import Resume
from app.models.run import Run
from app.models.skill import Skill, SkillAlias, UserSkill
from app.models.user import User

__all__ = [
    "Base",
    "Course",
    "CourseEmbedding",
    "CourseSkill",
    "JobPosting",
    "JobSkill",
    "LlmCall",
    "Plan",
    "Resume",
    "Run",
    "Skill",
    "SkillAlias",
    "User",
    "UserSkill",
]
