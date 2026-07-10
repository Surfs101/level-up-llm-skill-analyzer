"""In-process loader for the canonical skill taxonomy.

Every downstream component — the matcher, gap analysis, the audit CLI — reads the
taxonomy through this module rather than touching skills.json directly. The data
is loaded and validated once, then memoized; tests clear the cache to reload.

This is pure data access. No FlashText here — the matcher (matcher.py) builds its
keyword index from get_surface_to_id_map(), which is the single keyset that makes
extraction work.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# backend/app/nlp/taxonomy.py -> parents[2] is backend/, the data root. Resolved
# from this file, not the cwd, so it works no matter where pytest/uv is invoked.
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "taxonomy"
SKILLS_PATH = DATA_DIR / "skills.json"
CATEGORIES_PATH = DATA_DIR / "categories.json"


@dataclass(frozen=True)
class Skill:
    id: str
    canonical_name: str
    category: str
    priority_rank: int
    aliases: tuple[str, ...]


@lru_cache(maxsize=1)
def get_all_skills() -> tuple[Skill, ...]:
    """Load, validate, and return every skill. Memoized for the process life.

    Call get_all_skills.cache_clear() in tests to force a reload (e.g. after
    monkeypatching the JSON paths).
    """
    category_ranks = get_category_ranks()
    raw_skills = json.loads(SKILLS_PATH.read_text())

    skills = []
    for entry in raw_skills:
        validate_entry(entry, category_ranks)
        skills.append(
            Skill(
                id=entry["id"],
                canonical_name=entry["canonical_name"],
                category=entry["category"],
                priority_rank=entry["priority_rank"],
                aliases=tuple(entry["aliases"]),
            )
        )
    return tuple(skills)


@lru_cache(maxsize=1)
def get_category_ranks() -> dict[str, int]:
    """Map each category name to its priority_rank, from categories.json."""
    categories = json.loads(CATEGORIES_PATH.read_text())
    return {name: meta["priority_rank"] for name, meta in categories.items()}


def validate_entry(entry: dict[str, object], category_ranks: dict[str, int]) -> None:
    """Defense in depth beyond the integrity test: a malformed skills.json must
    fail loudly at load, not silently feed bad data into the matcher."""
    category = entry.get("category")
    if category not in category_ranks:
        raise ValueError(
            f"skill {entry.get('id')!r} has category {category!r} not defined in categories.json"
        )
    expected_rank = category_ranks[category]
    if entry.get("priority_rank") != expected_rank:
        raise ValueError(
            f"skill {entry.get('id')!r} has priority_rank {entry.get('priority_rank')!r} "
            f"but category {category!r} expects {expected_rank}"
        )


@lru_cache(maxsize=1)
def get_skill_index() -> dict[str, Skill]:
    """Internal: id -> Skill, for O(1) lookups."""
    return {skill.id: skill for skill in get_all_skills()}


def get_skill_by_id(skill_id: str) -> Skill | None:
    return get_skill_index().get(skill_id)


def get_priority_rank(skill_id: str) -> int:
    """Priority rank for a skill id. Raises KeyError if the id is unknown."""
    return get_skill_index()[skill_id].priority_rank


def get_category(skill_id: str) -> str:
    """Category for a skill id. Raises KeyError if the id is unknown."""
    return get_skill_index()[skill_id].category


@lru_cache(maxsize=1)
def get_surface_to_id_map() -> dict[str, str]:
    """The keyset the matcher indexes on: every lowercased surface form -> skill id.

    For each skill we register three kinds of form, all lowercased and all
    pointing at the same id:
      - the canonical_name (what a JD usually writes),
      - every alias,
      - the id itself — so slugs like csharp/cpp/fsharp are matchable even though
        the integrity test forbids storing an id as an alias.

    If any surface form ever resolved to two different ids the matcher would be
    ambiguous, so we treat that as a hard error even though the integrity test
    should already make it impossible.
    """
    surface_to_id: dict[str, str] = {}
    for skill in get_all_skills():
        forms = [skill.canonical_name.lower(), skill.id, *skill.aliases]
        for form in forms:
            existing = surface_to_id.get(form)
            if existing is not None and existing != skill.id:
                raise ValueError(
                    f"surface form {form!r} maps to both {existing!r} and {skill.id!r}"
                )
            surface_to_id[form] = skill.id
    return surface_to_id
