# `companies.json` — Greenhouse board allowlist

The list of Greenhouse board slugs Pipeline 2 is allowed to fetch. It doubles as the
**SSRF allowlist** (`app/greenhouse/client.py` refuses any slug not in this file), so
only add slugs you trust.

## Format

A plain JSON array of lowercase board slugs (the `{company}` in
`boards-api.greenhouse.io/v1/boards/{company}/jobs`). Entries must be unique and
non-empty (enforced by `tests/unit/test_companies_json.py`).

## Provenance & how to extend

This is a **curated starter set (~25), not the full ~200** the design targets — it's
deliberately extendable. The slugs are real companies commonly known to use Greenhouse
public boards, but board tokens change and some companies move to other ATSs, so
**verify each before relying on it** and prune any that don't resolve:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true"
# 200 = valid board, 404 = wrong/stale slug (drop it — a bad slug just 404s and is skipped)
```

A 404 is harmless at runtime (the fetch step logs and skips that company), but keeping
the list clean avoids wasted requests. Grow toward ~200 as you validate more boards.
