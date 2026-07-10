"""Tests for app/nlp/taxonomy.py — the taxonomy loader.

These assert the loader returns the right shape and, crucially, that the surface
map exposes ids (like "csharp") as matchable forms — the keystone of the whole
matcher design.
"""

import json

import pytest

from app.nlp import taxonomy


def test_all_skills_load_with_correct_count() -> None:
    skills = taxonomy.get_all_skills()
    on_disk = json.loads(taxonomy.SKILLS_PATH.read_text())
    assert len(skills) == len(on_disk)
    assert skills, "taxonomy loaded no skills"


def test_get_skill_by_id_python() -> None:
    python = taxonomy.get_skill_by_id("python")
    assert python is not None
    assert python.category == "language"
    assert python.priority_rank == 1
    assert python.canonical_name == "Python"


def test_get_skill_by_id_unknown_returns_none() -> None:
    assert taxonomy.get_skill_by_id("definitely-not-a-skill") is None


def test_surface_map_includes_canonical_alias_and_id() -> None:
    surface = taxonomy.get_surface_to_id_map()

    # canonical_name form
    assert surface["python"] == "python"
    # alias form
    assert surface["py"] == "python"
    # id form — an id that is NOT stored as an alias must still be matchable
    assert "csharp" not in taxonomy.get_skill_by_id("csharp").aliases
    assert surface["csharp"] == "csharp"


def test_surface_map_has_no_colliding_keys() -> None:
    # get_surface_to_id_map raises on any collision; reaching here means none.
    surface = taxonomy.get_surface_to_id_map()
    valid_ids = {skill.id for skill in taxonomy.get_all_skills()}
    assert all(skill_id in valid_ids for skill_id in surface.values())


def test_get_priority_rank_raises_keyerror_on_unknown() -> None:
    with pytest.raises(KeyError):
        taxonomy.get_priority_rank("definitely-not-a-skill")


def test_get_category_returns_category() -> None:
    assert taxonomy.get_category("python") == "language"
