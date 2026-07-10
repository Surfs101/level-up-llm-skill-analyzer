"""Build the canonical skill taxonomy.

Transforms data/taxonomy/skills_raw.json (the pristine seed) into
data/taxonomy/skills.json — the single source of truth the whole system rests
on. It generates slug ids, injects priority ranks from categories.json,
normalizes aliases, adds the technique category and a few missing canonicals,
recategorizes RAG, merges duplicate entries, and de-conflicts alias collisions.

The transform is idempotent: running it twice produces a byte-identical
skills.json. Pass --check to verify the on-disk file matches a fresh build
(used in CI) without writing anything.

Output entry shape, in this exact key order:
    {"id", "canonical_name", "category", "priority_rank", "aliases",
     "is_bundle": false, "bundle_expands_to": null}
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

TAXONOMY_DIR = Path(__file__).resolve().parent.parent / "data" / "taxonomy"
RAW_PATH = TAXONOMY_DIR / "skills_raw.json"
SKILLS_PATH = TAXONOMY_DIR / "skills.json"
CATEGORIES_PATH = TAXONOMY_DIR / "categories.json"

# Slug overrides for canonical names the general rule would mangle into
# something empty or meaningless. Add to this dict if the integrity test ever
# reports an empty/invalid/duplicate slug.
SLUG_OVERRIDES = {
    ".NET": "dotnet",
    ".NET Framework": "dotnet-framework",
    ".NET MAUI": "dotnet-maui",
    "C++": "cpp",
    "C#": "csharp",
    "F#": "fsharp",
    "F*": "fstar",
    "Q#": "qsharp",
    "Objective-C++": "objective-cpp",
}

# Technique entries (category "technique"). None exist in the raw seed — these
# are the high-signal phrases JDs filter on. (canonical_name, seed aliases).
TECHNIQUE_ENTRIES = [
    ("Machine Learning", ["ml"]),
    ("Deep Learning", ["dl"]),
    ("Natural Language Processing", ["nlp"]),
    ("Computer Vision", ["cv"]),
    ("Reinforcement Learning", ["rl"]),
    ("Large Language Models", ["llm", "llms", "large language model"]),
    ("Generative AI", ["genai", "gen ai"]),
    ("Prompt Engineering", []),
    ("Fine-tuning", ["finetuning", "fine tuning", "fine-tune", "fine tune"]),
    ("Embeddings", []),
    ("Vector Search", []),
    ("Semantic Search", []),
    ("MLOps", []),
    ("DataOps", []),
    ("Data Analysis", []),
    ("Data Science", []),
    ("Data Engineering", []),
    ("Data Modeling", []),
    ("Data Visualization", ["dataviz", "data viz", "data visualisation"]),
    ("ETL", []),
    ("ELT", []),
    ("Feature Engineering", []),
    ("Statistical Analysis", []),
    ("A/B Testing", ["ab testing", "a/b testing", "split testing"]),
    ("Time Series Analysis", ["time series", "time-series"]),
    ("Predictive Modeling", []),
    ("Classification", []),
    ("Regression", []),
    ("Clustering", []),
    ("Recommendation Systems", ["recsys", "recommender systems"]),
    ("Anomaly Detection", []),
    ("Object-Oriented Programming", ["oop"]),
    ("Functional Programming", ["fp"]),
    ("Test-Driven Development", ["tdd"]),
    ("Behavior-Driven Development", ["bdd"]),
    ("Agile", []),
    ("Scrum", []),
    ("Kanban", []),
    ("CI/CD", ["cicd", "ci cd", "continuous integration"]),
    ("DevOps", []),
    ("Microservices", ["microservice"]),
    ("Monorepo", []),
    ("Serverless Architecture", ["serverless"]),
    ("Containerization", []),
    ("Distributed Systems", []),
    # "eda" dropped: uppercase "EDA" usually means exploratory data analysis, not
    # this. Require the full phrase (canonical + the spaced form below).
    ("Event-Driven Architecture", ["event driven architecture"]),
    ("Domain-Driven Design", ["ddd"]),
    ("System Design", []),
    ("API Design", []),
    ("Database Design", []),
    ("Performance Optimization", []),
    ("Caching", []),
    ("Load Balancing", []),
    ("Unit Testing", []),
    ("Integration Testing", []),
    ("End-to-End Testing", ["e2e testing", "end to end testing"]),
    ("Load Testing", []),
    ("Security Testing", []),
    ("Threat Modeling", []),
    ("Authentication", ["authn"]),
    ("Authorization", ["authz"]),
    ("Encryption", []),
    ("Cryptography", ["crypto"]),
    ("Monitoring", []),
    ("Logging", []),
    ("Observability", []),
    ("Site Reliability Engineering", ["sre"]),
    ("Web Scraping", ["scraping"]),
    ("Stream Processing", []),
    ("Batch Processing", []),
    ("Event Streaming", []),
    ("Web Development", ["web dev"]),
    ("Mobile Development", ["mobile dev"]),
    # Area-technique skills match only on their FULL phrase, never a bare word
    # ("backend"/"frontend"/"full stack" are too generic — they fire on section
    # headers and prose). The canonical_name already provides the base phrase
    # ("Backend Development" -> surface "backend development"); these add the
    # other unambiguous phrase forms. Bare "backend"/"frontend"/"full stack"/
    # "fullstack" are intentionally absent.
    ("Backend Development", ["backend engineer", "backend developer"]),
    ("Frontend Development", ["frontend engineer", "frontend developer"]),
    (
        "Full-Stack Development",
        [
            "full stack development",
            "full stack engineer",
            "full stack developer",
            "fullstack developer",
            "fullstack engineer",
        ],
    ),
    ("Cloud Computing", []),
    ("Single Sign-On", ["sso"]),
    ("Multi-factor Authentication", ["mfa", "2fa", "two-factor authentication"]),
]

# Canonicals missing from the seed. (canonical_name, category, seed aliases).
MISSING_CANONICALS = [
    ("C", "language", ["clang"]),
    ("R", "language", ["rlang", "r-lang"]),
    ("Octave", "language", []),
    ("Pandoc", "tool", []),
    ("OpenTofu", "devops", ["opentofu"]),
]

# Duplicate canonicals to merge: keep the first, delete the second, fold the
# deleted entry's aliases into the kept one.
MERGES = [
    ("Eclipse", "Eclipse IDE"),
    ("Jenkins", "Jenkins CI"),
    ("Spring Framework", "Spring"),  # "Spring Boot" stays a separate entry
]

# Cross-entry alias collisions: an alias that really belongs to a DIFFERENT
# entry's canonical/id. Drop it from the entry listed here. Redundant
# self-aliases (an alias equal to its own entry's id or canonical) are removed
# automatically and do not need listing. Extend this if the integrity test
# surfaces a new cross-entry collision.
CROSS_ENTRY_ALIAS_DROPS = {
    "JavaScript": {"node"},  # Node.js is its own entry
    "HCL": {"terraform", "opentofu"},  # Terraform and OpenTofu are their own entries
    "Shell": {"bash", "shell-script"},  # Bash and "Shell script" are their own entries
    "Common Lisp": {"lisp"},  # Lisp is its own entry
    "Emacs Lisp": {"emacs"},  # Emacs is its own entry
    "Pascal": {"delphi"},  # Delphi is its own entry
    "Visual Basic .NET": {"visual basic"},  # ambiguous between the two VB entries
    "Visual Basic 6.0": {"visual basic"},
    "MATLAB": {"octave"},  # Octave is its own entry
    "Markdown": {"pandoc"},  # Pandoc is its own entry
    "Makefile": {"make"},  # Make is its own entry
    "Vim Script": {"vim"},  # Vim is its own entry
}

# Overly-generic aliases to drop: ordinary English words that slipped in (mostly
# via the gpt-4o-mini alias pass, plus one stale seed alias) and cause false
# positives on normal prose — e.g. "be", "do", "glue code", "cross-functional
# teams", "batch processing". Surfaced by the matcher F1 corpus. The validator in
# generate_aliases.py can't catch these (they collide with nothing in the
# taxonomy), so they are dropped here at build time. Keyed by canonical_name.
OVERLY_GENERIC_ALIAS_DROPS = {
    "Berry": {"be"},
    "DigitalOcean": {"do"},
    "Batchfile": {"batch"},
    "AWS Glue": {"glue"},  # "aws glue" alias is kept
    "Microsoft Teams": {"teams"},  # "microsoft teams" / "ms teams" are kept
    "C#": {"cake"},  # stale seed alias; Cake is a build tool, not C#
}

# RULE — drop whole entries whose only matchable surface is a common English word
# or a single character. The surface map (taxonomy.get_surface_to_id_map) always
# emits an entry's canonical_name and id as keywords, so when the canonical IS the
# poison word an alias-drop cannot remove it — only deleting the entry can. These
# esoteric one-word-named languages/tools fire on ordinary prose ("make sure",
# "the rest", "data processing", "basic knowledge") far more often than they name
# a real skill, so the case-insensitive matcher cannot keep them without wrecking
# precision.
# NOTE: the capitalized form of each of these (Make/Move/Just/Clean/Red/Reason/
# Basic/Processing/Linear...) ALSO opens sentences in ordinary prose, so a
# case-sensitive rescue (Part A / matcher.py) does NOT help them — they stay out.
# The one exception is R: a single uppercase letter rarely starts a prose word, so
# R is RESTORED here and matched case-sensitively as "R" (see CASE_SENSITIVE_
# SURFACES in matcher.py). Less is NOT restored here — see RECALL_ALIAS_ADDITIONS.
# Keyed by exact canonical_name.
DROP_ENTRIES = {
    "Self",
    "Max",
    "GAP",
    "Make",
    "Move",
    "Just",
    "Red",
    "Teal",
    "Clean",
    "BASIC",
    "Reason",
    "Clarity",
    "Processing",
    "Parcel",
    "Io",
    "Fluent",
    "Linear",
}

# RULE — drop aliases that are ordinary words, greedy substrings, or compound
# prefixes that collide with an UNRELATED skill (or with normal prose / email
# addresses). Unlike OVERLY_GENERIC_ALIAS_DROPS these collide with a *specific*
# wrong sense, listed in the comment. Keyed by canonical_name.
SUBSTRING_COLLISION_DROPS = {
    "OpenEdge ABL": {"progress"},  # "progress" the English word
    "PHP": {"inc"},  # fires on "Inc" in company names
    "Azure Functions": {"functions"},  # "functions" the English word
    "Microsoft Access": {"access"},  # "access" the English word
    "Microsoft Exchange": {"exchange"},  # "exchange" the English word
    "Microsoft Active Directory": {"ad"},  # "ad", a 2-char fragment
    "Backbone.js": {"backbone"},  # "backbone" the English word
    "Eclipse Jersey": {"jersey"},  # "Jersey" (e.g. New Jersey)
    "Solid.js": {"solid"},  # "Solid" / SOLID principles ("solidjs" is kept)
    "Microsoft Office": {"office"},  # physical "office" ("microsoft office" kept)
    "Adobe Illustrator": {"ai"},  # "AI" = artificial intelligence
    "Google Gmail": {"gmail"},  # fires on "@gmail.com" ("google gmail" kept)
    # Greedy compound prefix: "openai gpt" swallows "OpenAI GPT-4o", blocking
    # both `openai` and `gpt-4`. Dropping it lets "OpenAI" -> openai and
    # "GPT-4o" -> gpt-4 resolve independently. ("chatgpt" etc. are kept.)
    "OpenAI ChatGPT": {"openai gpt"},
    # "transformers" matches inside "sentence-transformers" (a different, unmapped
    # library); too collision-prone. ("hf transformers" + canonical are kept.)
    "Hugging Face Transformers": {"transformers"},
    # "tf" is unrescuable even case-sensitively: uppercase "TF" overwhelmingly
    # means term-frequency ("TF-IDF"), not TensorFlow. ("tensorflow"/"tensor flow"
    # are kept.)
    "TensorFlow": {"tf"},
}

# RULE — add high-value recall aliases: unambiguous skill surfaces (no English
# words) that the seed lacked. Aliases equal to the canonical (lowercased) are
# omitted — the canonical is already a surface — to avoid an alias/canonical
# collision. Keyed by canonical_name.
RECALL_ALIAS_ADDITIONS = {
    "RESTful API": {"restful", "rest apis", "restful apis"},  # "rest api" already seeded
    "WebSockets": {"websocket"},
    "Google Analytics": {"ga4"},
    # Less (CSS) is restored from DROP_ENTRIES but its bare name "less"/"Less"
    # collides with prose in BOTH cases ("less than", sentence-opening "Less"), so
    # case-sensitivity can't rescue it the way it does R. Instead it is reachable
    # ONLY via the unambiguous compound forms below; the bare "less" surface is
    # suppressed from the case-insensitive matcher (matcher.EXCLUDED_SURFACES).
    "Less": {"less css", "lesscss"},  # "less-css" already seeded
    # Roc (language): bare "roc"/"ROC" overwhelmingly means the ROC/AUC metric, not
    # this esoteric language. The bare "roc" surface is suppressed in
    # matcher.EXCLUDED_SURFACES; Roc stays reachable via the compound form below.
    "Roc": {"roc lang", "roc-lang"},
}


def slugify(canonical_name: str) -> str:
    """Derive a stable lowercase slug id from a canonical name."""
    if canonical_name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[canonical_name]
    slug = canonical_name.lower().replace("&", "and")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)  # runs of non-slug chars -> "-"
    slug = re.sub(r"-+", "-", slug)  # collapse repeats
    return slug.strip("-")


def normalize_aliases(aliases: list[str]) -> list[str]:
    """Lowercase, strip, drop empties and <2-char aliases, dedupe in order."""
    seen: list[str] = []
    for alias in aliases:
        cleaned = alias.strip().lower()
        if len(cleaned) >= 2 and cleaned not in seen:
            seen.append(cleaned)
    return seen


def merge_duplicates(raw: list[dict]) -> list[dict]:
    """Drop each merge's second entry, folding its aliases into the kept one."""
    folded_aliases: dict[str, list[str]] = {keep: [] for keep, _ in MERGES}
    to_delete = {delete for _, delete in MERGES}
    for keep, delete in MERGES:
        deleted = next(e for e in raw if e["canonical_name"] == delete)
        folded_aliases[keep] += deleted["aliases"]

    entries = []
    for entry in raw:
        if entry["canonical_name"] in to_delete:
            continue
        entry = dict(entry)
        entry["aliases"] = entry["aliases"] + folded_aliases.get(entry["canonical_name"], [])
        entries.append(entry)
    return entries


def recategorize_rag(entries: list[dict]) -> None:
    """Move RAG from tool to technique, keeping its existing aliases."""
    for entry in entries:
        if entry["canonical_name"] == "RAG":
            entry["category"] = "technique"


def new_entry(canonical_name: str, category: str, aliases: list[str]) -> dict:
    return {
        "canonical_name": canonical_name,
        "category": category,
        "aliases": list(aliases),
        "is_bundle": False,
        "bundle_expands_to": None,
    }


def assign_ids(entries: list[dict]) -> None:
    """Set a unique slug id on every entry, disambiguating collisions."""
    for entry in entries:
        entry["id"] = slugify(entry["canonical_name"])

    colliding = {slug for slug, count in Counter(e["id"] for e in entries).items() if count > 1}
    for entry in entries:
        if entry["id"] in colliding:
            entry["id"] = f"{entry['id']}-{entry['category']}"

    dupes = sorted(slug for slug, count in Counter(e["id"] for e in entries).items() if count > 1)
    if dupes:
        raise SystemExit(f"unresolvable slug collisions (add to SLUG_OVERRIDES): {dupes}")


def drop_redundant_self_aliases(entries: list[dict]) -> None:
    """Remove any alias equal to its own entry's id or canonical name."""
    for entry in entries:
        own = {entry["id"], entry["canonical_name"].strip().lower()}
        entry["aliases"] = [alias for alias in entry["aliases"] if alias not in own]


def build_entries() -> list[dict]:
    raw = json.loads(RAW_PATH.read_text())
    categories = json.loads(CATEGORIES_PATH.read_text())

    entries = merge_duplicates(raw)
    recategorize_rag(entries)
    entries += [new_entry(name, "technique", aliases) for name, aliases in TECHNIQUE_ENTRIES]
    entries += [new_entry(name, cat, aliases) for name, cat, aliases in MISSING_CANONICALS]

    entries = [entry for entry in entries if entry["canonical_name"] not in DROP_ENTRIES]

    for entry in entries:
        additions = RECALL_ALIAS_ADDITIONS.get(entry["canonical_name"], set())
        entry["aliases"] = normalize_aliases(entry["aliases"] + sorted(additions))
        dropped = CROSS_ENTRY_ALIAS_DROPS.get(entry["canonical_name"], set())
        dropped = dropped | OVERLY_GENERIC_ALIAS_DROPS.get(entry["canonical_name"], set())
        dropped = dropped | SUBSTRING_COLLISION_DROPS.get(entry["canonical_name"], set())
        entry["aliases"] = [alias for alias in entry["aliases"] if alias not in dropped]

    assign_ids(entries)
    drop_redundant_self_aliases(entries)

    for entry in entries:
        entry["priority_rank"] = categories[entry["category"]]["priority_rank"]

    shaped = [
        {
            "id": entry["id"],
            "canonical_name": entry["canonical_name"],
            "category": entry["category"],
            "priority_rank": entry["priority_rank"],
            "aliases": entry["aliases"],
            "is_bundle": False,
            "bundle_expands_to": None,
        }
        for entry in entries
    ]
    shaped.sort(key=lambda e: e["canonical_name"].lower())
    return shaped


def render_json(entries: list[dict]) -> str:
    return json.dumps(entries, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the canonical skill taxonomy.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the on-disk skills.json differs from a fresh build (no write).",
    )
    args = parser.parse_args()

    entries = build_entries()
    rendered = render_json(entries)
    alias_count = sum(len(e["aliases"]) for e in entries)

    if args.check:
        on_disk = SKILLS_PATH.read_text() if SKILLS_PATH.exists() else ""
        if on_disk != rendered:
            print(
                "skills.json is out of date — run: python scripts/build_taxonomy.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f"skills.json is up to date ({len(entries)} skills, {alias_count} aliases).")
        return

    SKILLS_PATH.write_text(rendered)
    print(f"wrote {SKILLS_PATH} — {len(entries)} skills, {alias_count} aliases")


if __name__ == "__main__":
    main()
