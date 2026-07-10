"""data/companies.json is a list of unique, non-empty Greenhouse board slugs."""

import json

from app.greenhouse.client import _COMPANIES_PATH as COMPANIES_PATH
from app.greenhouse.client import load_allowlist


def test_companies_json_is_a_clean_slug_list() -> None:
    slugs = json.loads(COMPANIES_PATH.read_text())

    assert isinstance(slugs, list)
    assert slugs, "companies.json must not be empty"
    assert all(isinstance(slug, str) and slug.strip() for slug in slugs), "slugs must be non-empty"
    assert len(slugs) == len(set(slugs)), "slugs must be unique"


def test_allowlist_loads_the_slugs() -> None:
    allowlist = load_allowlist()
    assert len(allowlist) > 0
    assert all(isinstance(slug, str) for slug in allowlist)
