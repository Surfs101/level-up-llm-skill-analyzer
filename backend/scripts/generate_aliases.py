"""Bulk-generate skill aliases with gpt-4o-mini.

Most of the 1,095 canonical skills have zero or very few aliases. That is the
single biggest precision risk in the system: skill extraction is rule-based
(FlashText, no fuzzy matching), so a JD that writes "postgres", "react.js", or
"fast api" simply will not match unless that surface form is a registered alias.
This script fills those gaps in batch.

Where aliases live (important): build_taxonomy.py rebuilds skills.json from
skills_raw.json on every run, so aliases written only to skills.json would be
wiped on the next build and break the --check idempotency contract. Therefore
accepted aliases are written back into skills_raw.json (the single source of
truth), and skills.json is then regenerated through build_taxonomy itself — same
serialization, still idempotent.

One consequence: technique entries and a handful of code-defined canonicals
(Octave, OpenTofu, Pandoc) do not exist in skills_raw.json — they are Python
lists inside build_taxonomy.py. We cannot durably attach generated aliases to
them via raw, so they are skipped here and logged. Their aliases are curated by
hand in build_taxonomy.py instead.

Usage:
    uv run python scripts/generate_aliases.py --dry-run --limit 50
    uv run python scripts/generate_aliases.py
    uv run python scripts/generate_aliases.py --resume

Requires OPENAI_API_KEY in the environment (or in backend/.env).
"""

import argparse
import json
import sys
from pathlib import Path

from openai import OpenAI

# build_taxonomy is the source of truth for serialization and the rebuild. We
# reuse its render + build functions so skills.json stays byte-identical to what
# a fresh build would produce.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_taxonomy  # noqa: E402

TAXONOMY_DIR = Path(__file__).resolve().parent.parent / "data" / "taxonomy"
RAW_PATH = TAXONOMY_DIR / "skills_raw.json"
SKILLS_PATH = TAXONOMY_DIR / "skills.json"
BACKUP_PATH = TAXONOMY_DIR / "skills.json.bak"
AUDIT_PATH = TAXONOMY_DIR / "aliases_generated.json"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

MODEL = "gpt-4o-mini"
BATCH_SIZE = 25
MAX_ALIASES_PER_ENTRY = 5

# The only characters an alias may contain. Matches the matcher's tokenization
# and the integrity test's expectations.
ALLOWED_ALIAS_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789 .-/+#")

PROMPT_HEADER = """\
For each technology below, return common case-insensitive aliases that appear in
software-engineering resumes and job descriptions.
Rules:
  - lowercase, stripped; allowed chars: a-z 0-9 space . - / + #
  - include abbreviations (k8s->Kubernetes, tf->TensorFlow), spacing variants
    (fast api->FastAPI), dotted variants (react.js->React)
  - EXCLUDE the canonical name itself, version numbers, file extensions, and
    marketing taglines
  - max 5 aliases per entry; quality over quantity
  - if none are good, return an empty array
Return STRICT JSON only: {"<id>": ["<alias>", ...], ...}
Entries:
"""


def main() -> None:
    args = parse_args()
    load_env_file()

    skills = json.loads(SKILLS_PATH.read_text())
    raw = json.loads(RAW_PATH.read_text())
    raw_canonicals = {entry["canonical_name"] for entry in raw}

    already_done = load_done_ids() if args.resume else set()
    eligible = select_eligible(skills, raw_canonicals, already_done)
    if args.limit is not None:
        eligible = eligible[: args.limit]

    skipped_non_raw = count_non_raw_eligible(skills, raw_canonicals, already_done)
    print(
        f"{len(eligible)} eligible raw-origin entries to process "
        f"(batch size {BATCH_SIZE}, model {MODEL})."
    )
    print(
        f"Skipping {skipped_non_raw} eligible non-raw entries (techniques + "
        f"code-defined canonicals) — their aliases live in build_taxonomy.py."
    )
    if not eligible:
        print("Nothing to do.")
        return

    validator = AliasValidator(skills)
    client = OpenAI()
    audit = load_audit() if args.resume else {}

    for batch_num, batch in enumerate(chunked(eligible, BATCH_SIZE), start=1):
        print(f"  batch {batch_num}: {len(batch)} entries...", flush=True)
        suggestions = call_model(client, batch)
        for entry in batch:
            proposed = suggestions.get(entry["id"], [])
            accepted, rejected = validator.review(entry, proposed)
            audit[entry["id"]] = {
                "canonical": entry["canonical_name"],
                "accepted": accepted,
                "rejected": rejected,
            }

    total_accepted = sum(len(rec["accepted"]) for rec in audit.values())
    print(f"Generated {total_accepted} accepted aliases across {len(audit)} entries.")

    if args.dry_run:
        write_json(AUDIT_PATH, audit)
        print(f"--dry-run: wrote audit trail to {AUDIT_PATH}; no taxonomy file touched.")
        return

    snapshot_skills()
    merge_into_raw(raw, audit)
    write_json(RAW_PATH, raw)
    rebuild_skills_json()
    write_json(AUDIT_PATH, audit)
    print(f"Wrote aliases into {RAW_PATH}, regenerated {SKILLS_PATH}, audit at {AUDIT_PATH}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk-generate skill aliases via gpt-4o-mini.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Call the API and write only the audit trail; touch no taxonomy file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N eligible entries (cheap test run).",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Skip entries already present in the audit trail."
    )
    return parser.parse_args()


def load_env_file() -> None:
    """Load KEY=VALUE lines from backend/.env into os.environ if present.

    We avoid a dotenv dependency for a one-off script; the OpenAI client reads
    OPENAI_API_KEY straight from the environment.
    """
    import os

    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# --- Selecting which entries get aliases -----------------------------------


def select_eligible(skills: list[dict], raw_canonicals: set[str], done: set[str]) -> list[dict]:
    """Eligible, raw-origin entries, sorted by canonical name for determinism."""
    eligible = [
        entry
        for entry in skills
        if entry["id"] not in done
        and entry["canonical_name"] in raw_canonicals
        and needs_aliases(entry)
        and not is_obscure_short(entry)
    ]
    eligible.sort(key=lambda e: e["canonical_name"].lower())
    return eligible


def needs_aliases(entry: dict) -> bool:
    """0 aliases, or 1 alias on a name with variants (multi-word or . / + #)."""
    aliases = entry.get("aliases", [])
    if len(aliases) == 0:
        return True
    return len(aliases) == 1 and has_likely_variants(entry["canonical_name"])


def has_likely_variants(name: str) -> bool:
    return len(name.split()) > 1 or any(char in name for char in ".+#/")


def is_obscure_short(entry: dict) -> bool:
    """A single short language name (Awk, Tcl, Zig, Lua, Nim) unlikely to have
    real aliases. The canonical itself is already the keyword; generating here
    only wastes tokens and risks junk. Restricted to languages so we never skip
    a short framework/cloud name like Vue or AWS."""
    name = entry["canonical_name"]
    return entry["category"] == "language" and " " not in name and name.isalpha() and len(name) <= 3


def count_non_raw_eligible(skills: list[dict], raw_canonicals: set[str], done: set[str]) -> int:
    return sum(
        1
        for entry in skills
        if entry["id"] not in done
        and entry["canonical_name"] not in raw_canonicals
        and needs_aliases(entry)
        and not is_obscure_short(entry)
    )


# --- Calling the model ------------------------------------------------------


def call_model(client: OpenAI, batch: list[dict]) -> dict[str, list[str]]:
    """Ask gpt-4o-mini for aliases for one batch. Returns {id: [alias, ...]}.

    A batch that errors or returns unparseable JSON yields no suggestions rather
    than aborting the whole run — the other batches still land.
    """
    prompt = build_prompt(batch)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as error:  # noqa: BLE001 — one bad batch must not kill the run
        print(f"    batch failed ({error}); skipping its entries.", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print("    batch returned non-object JSON; skipping.", file=sys.stderr)
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, list)}


def build_prompt(batch: list[dict]) -> str:
    lines = [
        f'  - id: "{entry["id"]}", canonical: "{entry["canonical_name"]}", '
        f'category: "{entry["category"]}"'
        for entry in batch
    ]
    return PROMPT_HEADER + "\n".join(lines)


# --- Validating generated aliases ------------------------------------------


class AliasValidator:
    """Validates aliases against the full taxonomy and against each other.

    The rules mirror the integrity test exactly, so anything this accepts keeps
    test_taxonomy_integrity green after the rebuild.
    """

    def __init__(self, skills: list[dict]) -> None:
        self.ids = {entry["id"] for entry in skills}
        self.canonicals = {entry["canonical_name"].strip().lower() for entry in skills}
        # alias -> owning id, so we can tell "already mine" from "belongs to another".
        self.alias_owner = {
            alias: entry["id"] for entry in skills for alias in entry.get("aliases", [])
        }
        # Every alias accepted so far this run, to enforce global first-wins.
        self.accepted_this_run: set[str] = set()

    def review(self, entry: dict, proposed: list[str]) -> tuple[list[str], list[dict]]:
        accepted: list[str] = []
        rejected: list[dict] = []
        own_canonical = entry["canonical_name"].strip().lower()
        own_aliases = set(entry.get("aliases", []))

        for raw_alias in proposed:
            if not isinstance(raw_alias, str):
                continue
            alias = raw_alias.strip().lower()
            reason = self._reject_reason(alias, entry["id"], own_canonical, own_aliases)
            if reason == "already present":
                continue  # already an alias of this entry — dedupe, not a rejection
            if reason:
                rejected.append({"alias": raw_alias, "reason": reason})
                continue
            accepted.append(alias)
            self.accepted_this_run.add(alias)
        return accepted, rejected

    def _reject_reason(
        self, alias: str, own_id: str, own_canonical: str, own_aliases: set[str]
    ) -> str | None:
        if len(alias) < 2:
            return "too short (<2 chars)"
        if any(char not in ALLOWED_ALIAS_CHARS for char in alias):
            return "contains disallowed characters"
        if alias in (own_id, own_canonical):
            return "equals its own id or canonical_name"
        if alias in self.ids:
            return "equals an id of another entry"
        if alias in self.canonicals:
            return "equals a canonical_name"
        owner = self.alias_owner.get(alias)
        if owner == own_id or alias in own_aliases:
            return "already present"
        if owner is not None:
            return "equals an existing alias of another entry"
        if alias in self.accepted_this_run:
            return "duplicate of an alias generated earlier this run"
        return None


# --- Writing results --------------------------------------------------------


def merge_into_raw(raw: list[dict], audit: dict) -> None:
    """Extend each raw entry's aliases with its accepted aliases (dedupe, keep
    order). Matched by canonical_name — every audited id is raw-origin."""
    by_canonical = {entry["canonical_name"]: entry for entry in raw}
    for record in audit.values():
        target = by_canonical.get(record["canonical"])
        if target is None:
            continue  # non-raw entry slipped through; nothing durable we can do
        existing = set(target["aliases"])
        for alias in record["accepted"]:
            if alias not in existing:
                target["aliases"].append(alias)
                existing.add(alias)


def rebuild_skills_json() -> None:
    """Regenerate skills.json from the updated raw, via build_taxonomy — same
    serialization, so build_taxonomy.py --check still passes."""
    entries = build_taxonomy.build_entries()
    SKILLS_PATH.write_text(build_taxonomy.render_json(entries))


def snapshot_skills() -> None:
    BACKUP_PATH.write_text(SKILLS_PATH.read_text())
    print(f"Snapshot: {SKILLS_PATH} -> {BACKUP_PATH}")


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_audit() -> dict:
    if AUDIT_PATH.exists():
        return json.loads(AUDIT_PATH.read_text())
    return {}


def load_done_ids() -> set[str]:
    return set(load_audit().keys())


def chunked(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


if __name__ == "__main__":
    main()
