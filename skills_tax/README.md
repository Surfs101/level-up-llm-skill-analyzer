Skills taxonomy seed. Populated separately. Format: see below.

Each entry in skills_seed.json is an object:
{
  "canonical_name": "FastAPI",
  "category": "framework",
  "aliases": ["fast api"],
  "is_bundle": false,
  "bundle_expands_to": null
}

Rules:
- canonical_name: unique, non-empty
- category: one of "language", "framework", "tool"
- aliases: lowercase, whitespace-collapsed. Trivial casing variants omitted.
- is_bundle: true for things like "MERN" that expand into multiple skills
- bundle_expands_to: null unless is_bundle=true, then array of canonical_name strings


## Authoring workflow

The taxonomy is authored as numbered chunk files under `data/chunks/`, then merged into a single `skills_seed.json`. Don't hand-edit `skills_seed.json` — it's a build artifact.

Chunk files use the same per-entry schema documented above. Each file is a JSON array. Filenames are numbered so they sort in author-intended order:

```
data/chunks/
  01_lang_mainstream.json
  02_lang_extra.json
  03_framework_web.json
  ...
```

To merge:

```sh
uv run python scripts/merge_chunks.py
```

The script:

- reads every `*.json` under `data/chunks/` in alphabetical order (so `01_` precedes `02_`, etc.);
- deduplicates by `canonical_name` — the first occurrence wins, a `WARN: duplicate ...` line is printed to stderr for every drop;
- validates the merged set with the same rules as the seeder, including bundle references (each name in `bundle_expands_to` must resolve to a `canonical_name` in the merged file);
- on success, writes `skills_seed.json` pretty-printed with 2-space indent and exits 0;
- on validation failure, prints all errors to stderr and exits 1 without touching `skills_seed.json`;
- on IO or JSON-parse failure, exits 2.

If `data/chunks/` is empty (only `.gitkeep`), the script exits 0 without modifying `skills_seed.json`.

After merging, load into Postgres with:

```sh
uv run python scripts/seed_skills.py
```

