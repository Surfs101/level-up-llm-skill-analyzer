"""Skill taxonomy + user skill-set models (design doc §6).

The canonical taxonomy lives in data/taxonomy/skills.json as the single source of
truth; these tables are its mirror in Postgres, loaded by
scripts/sync_taxonomy_to_db.py. Everything downstream keys off the skill id — a
stable lowercase slug (e.g. 'python', 'fastapi', 'node-js'), a string, never a UUID.

  - Skill        one canonical skill (the slug is its primary key)
  - SkillAlias   a lowercased surface form that resolves to a skill id
  - UserSkill    one skill in a user's dashboard set, tagged extracted vs manual

Note course_skills (in course.py) stores skill_id as a plain string, NOT a FK to
this table, because that model predates skills living in Postgres. UserSkill does
use a real FK — a user skill must reference a skill that exists.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # slug, e.g. 'fastapi'
    display_name: Mapped[str] = mapped_column(String, nullable=False)  # canonical_name
    # One of the 8 categories: language|framework|library|database|cloud|devops|tool|technique
    category: Mapped[str] = mapped_column(String, nullable=False)
    priority_rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    alias: Mapped[str] = mapped_column(String, primary_key=True)  # lowercased surface form
    skill_id: Mapped[str] = mapped_column(
        String, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"), primary_key=True)
    # 'extracted' (from a resume) or 'manual' (added/kept by the user). The merge
    # rule on resume re-upload is: DELETE WHERE source='extracted', then re-insert.
    source: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
