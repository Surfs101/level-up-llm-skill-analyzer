"""Integrity tests for the canonical skill taxonomy.

Written test-first (TDD): they run before scripts/build_taxonomy.py produces
data/taxonomy/skills.json. Until that file exists, every test fails with a clear
assertion message rather than crashing. Each rule is its own test function so a
single violation does not mask the others.

The whole system's correctness rests on skills.json, so these 11 assertions
gate any code that depends on the taxonomy.
"""

import json
import re
from collections import Counter
from pathlib import Path

TAXONOMY_DIR = Path(__file__).resolve().parents[2] / "data" / "taxonomy"
SKILLS_PATH = TAXONOMY_DIR / "skills.json"
CATEGORIES_PATH = TAXONOMY_DIR / "categories.json"

# id must be a lowercase slug: groups of [a-z0-9] joined by single - or _.
ID_SLUG_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


def load_skills() -> tuple[list[dict], bool]:
    """Return (skills, missing). missing is True when skills.json is absent."""
    if not SKILLS_PATH.exists():
        return [], True
    with SKILLS_PATH.open() as f:
        return json.load(f), False


def load_categories() -> dict:
    with CATEGORIES_PATH.open() as f:
        return json.load(f)


SKILLS, SKILLS_MISSING = load_skills()
CATEGORIES = load_categories()


def require_skills() -> None:
    """Fail cleanly (not crash) when skills.json hasn't been built yet."""
    assert not SKILLS_MISSING, (
        f"skills.json missing at {SKILLS_PATH} — run scripts/build_taxonomy.py to generate it"
    )


def test_skills_file_exists() -> None:
    assert not SKILLS_MISSING, (
        f"skills.json missing at {SKILLS_PATH} — run scripts/build_taxonomy.py to generate it"
    )
    assert SKILLS, "skills.json is present but contains no entries"


def test_all_ids_unique() -> None:
    require_skills()
    for i, entry in enumerate(SKILLS):
        sid = entry.get("id")
        assert isinstance(sid, str) and sid, f"entry {i} has a missing or non-string id: {sid!r}"
    ids = [entry["id"] for entry in SKILLS]
    dupes = sorted(sid for sid, count in Counter(ids).items() if count > 1)
    assert not dupes, f"duplicate ids: {dupes}"


def test_id_is_slug() -> None:
    require_skills()
    bad = [entry.get("id", "") for entry in SKILLS if not ID_SLUG_RE.match(entry.get("id", ""))]
    assert not bad, f"ids that are not valid slugs: {bad}"


def test_canonical_name_present() -> None:
    require_skills()
    bad = [
        i
        for i, entry in enumerate(SKILLS)
        if not (isinstance(entry.get("canonical_name"), str) and entry["canonical_name"].strip())
    ]
    assert not bad, f"entries with missing or empty canonical_name: indices {bad}"


def test_canonical_names_unique() -> None:
    require_skills()
    lowered = [entry.get("canonical_name", "").strip().lower() for entry in SKILLS]
    dupes = sorted(name for name, count in Counter(lowered).items() if name and count > 1)
    assert not dupes, f"duplicate canonical_names (case-insensitive): {dupes}"


def test_category_valid() -> None:
    require_skills()
    valid = set(CATEGORIES)
    bad = sorted({entry.get("category") for entry in SKILLS if entry.get("category") not in valid})
    assert not bad, f"categories not defined in categories.json: {bad}"


def test_priority_rank_matches_category() -> None:
    require_skills()
    mismatches = []
    for entry in SKILLS:
        category = entry.get("category")
        if category in CATEGORIES:
            expected = CATEGORIES[category]["priority_rank"]
            if entry.get("priority_rank") != expected:
                mismatches.append((entry.get("id"), category, entry.get("priority_rank"), expected))
    assert not mismatches, f"priority_rank != category rank (id, cat, got, want): {mismatches}"


def test_aliases_lowercase_nonempty() -> None:
    require_skills()
    bad = []
    for entry in SKILLS:
        for alias in entry.get("aliases", []):
            if not isinstance(alias, str) or alias != alias.strip().lower() or len(alias) < 2:
                bad.append((entry.get("id"), alias))
    assert not bad, f"aliases not lowercased/stripped/len>=2: {bad}"


def test_aliases_globally_unique() -> None:
    require_skills()
    all_aliases = [alias for entry in SKILLS for alias in entry.get("aliases", [])]
    dupes = sorted(alias for alias, count in Counter(all_aliases).items() if count > 1)
    assert not dupes, f"aliases appearing on more than one entry: {dupes}"


def test_alias_never_collides_with_any_canonical() -> None:
    require_skills()
    canonicals = {entry.get("canonical_name", "").strip().lower() for entry in SKILLS}
    collisions = []
    for entry in SKILLS:
        for alias in entry.get("aliases", []):
            if alias.strip().lower() in canonicals:
                collisions.append((entry.get("id"), alias))
    assert not collisions, f"aliases colliding with a canonical_name: {collisions}"


def test_alias_never_collides_with_any_id() -> None:
    require_skills()
    ids = {entry.get("id") for entry in SKILLS}
    collisions = []
    self_referencing = []
    for entry in SKILLS:
        own_canonical = entry.get("canonical_name", "").strip().lower()
        for alias in entry.get("aliases", []):
            if alias in ids:
                collisions.append((entry.get("id"), alias))
            if alias.strip().lower() == own_canonical:
                self_referencing.append((entry.get("id"), alias))
    assert not collisions, f"aliases equal to some id: {collisions}"
    assert not self_referencing, (
        f"entries listing their own canonical_name as alias: {self_referencing}"
    )
