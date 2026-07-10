"""Taxonomy drift detector — a read-only CLI run periodically over recent text.

    python -m app.nlp.audit <dir>

Skill extraction is rule-based, so a skill the taxonomy doesn't know is a skill
the system is blind to. This tool scans a directory of .txt files (resumes/JDs),
finds tokens that LOOK like technologies (CamelCase, dotted, all-caps acronyms,
tech-shaped suffixes) but that the matcher did NOT recognize, and surfaces the
ones recurring across multiple files as candidate taxonomy gaps for a human to
review.

It is strictly read-only with respect to the taxonomy: it imports the matcher and
loader but never writes skills.json. Accepted gaps are added by hand through
scripts/build_taxonomy.py, never by this tool.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import TypedDict

from app.nlp.matcher import extract_skill_ids
from app.nlp.taxonomy import get_category


class CandidateGap(TypedDict):
    token: str
    occurrences: int
    files: list[str]


class AuditReport(TypedDict):
    scanned_files: int
    total_matches: int
    matches_by_category: dict[str, int]
    candidate_gaps: list[CandidateGap]


# Common words that happen to be capitalized or all-caps in resumes/JDs (section
# headers, conjunctions) but are not technologies. Keeps ordinary English out of
# the candidate list.
STOPWORDS = {
    "and",
    "or",
    "the",
    "for",
    "with",
    "a",
    "an",
    "to",
    "of",
    "in",
    "on",
    "at",
    "is",
    "are",
    "as",
    "by",
    "we",
    "i",
    "you",
    "our",
    "your",
    "they",
    "skills",
    "experience",
    "education",
    "summary",
    "projects",
    "work",
    "senior",
    "junior",
    "lead",
    "engineer",
    "developer",
    "manager",
    "team",
    "years",
    "year",
    "strong",
    "excellent",
    "using",
    "used",
    "built",
    "build",
    "eg",
    "ie",
    "etc",
    "vs",
    "am",
    "pm",
}

# Tech-shaped suffixes: a token ending in one of these reads like a technology.
TECH_SUFFIXES = (".js", ".io", ".net", "sdk", "db", "api", "ql", "ml", "ops")

# Abbreviations that are dotted but are plain English, never technologies.
DOTTED_ENGLISH = {"e.g.", "i.e.", "etc.", "vs.", "a.m.", "p.m."}

# A run of letters/digits, keeping internal . + # / - so Node.js, C++, CI/CD,
# and react-native survive tokenization intact.
TOKEN_RE = re.compile(r"[A-Za-z0-9][\w.+#/-]*")

MAX_NGRAM = 3


def main() -> None:
    args = parse_args()
    report = scan_directory(Path(args.directory), args.min_files)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print_summary(report, output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect taxonomy gaps in .txt files.")
    parser.add_argument("directory", help="Directory of .txt resumes/JDs to scan.")
    parser.add_argument(
        "--min-files",
        type=int,
        default=2,
        help="Flag a candidate only if it recurs in >= this many files.",
    )
    parser.add_argument(
        "--output", default="audit_report.json", help="Where to write the JSON report."
    )
    return parser.parse_args()


def scan_directory(directory: Path, min_files: int) -> AuditReport:
    """Build the audit report for every .txt file in the directory.

    Pure with respect to the filesystem output — it only reads. main() is the
    only thing that writes the report file.
    """
    files = sorted(directory.glob("*.txt")) if directory.is_dir() else []

    matches_by_category: Counter[str] = Counter()
    total_matches = 0
    # candidate token -> set of file names it appeared in, and how many times.
    candidate_files: dict[str, set[str]] = {}
    candidate_counts: Counter[str] = Counter()

    for path in files:
        text = path.read_text(errors="ignore")

        matched_ids = extract_skill_ids(text)
        total_matches += len(matched_ids)
        for skill_id in matched_ids:
            matches_by_category[get_category(skill_id)] += 1

        for token in find_unmatched_candidates(text):
            candidate_counts[token] += 1
            candidate_files.setdefault(token, set()).add(path.name)

    # Sort tokens first (str/int keys, easy to reason about), then shape the gaps.
    recurring_tokens = [
        token for token, names in candidate_files.items() if len(names) >= min_files
    ]
    recurring_tokens.sort(key=lambda token: (-candidate_counts[token], token.lower()))
    candidate_gaps: list[CandidateGap] = [
        {
            "token": token,
            "occurrences": candidate_counts[token],
            "files": sorted(candidate_files[token]),
        }
        for token in recurring_tokens
    ]

    return {
        "scanned_files": len(files),
        "total_matches": total_matches,
        "matches_by_category": dict(sorted(matches_by_category.items())),
        "candidate_gaps": candidate_gaps,
    }


def find_unmatched_candidates(text: str) -> set[str]:
    """Skill-shaped 1-3 word phrases in the text that the matcher did not match.

    We drop a longer phrase when a shorter flagged phrase already sits inside it,
    so "Senior FastAPI role" collapses to just "FastAPI" — the real signal.
    """
    tokens = [token.strip("./-") for token in TOKEN_RE.findall(text)]
    tokens = [token for token in tokens if token]

    flagged: list[str] = []
    for size in range(1, MAX_NGRAM + 1):
        for start in range(len(tokens) - size + 1):
            gram_tokens = tokens[start : start + size]
            gram = " ".join(gram_tokens)
            if is_skill_shaped(gram_tokens) and not extract_skill_ids(gram):
                flagged.append(gram)

    return {gram for gram in flagged if not contains_shorter_candidate(gram, flagged)}


def contains_shorter_candidate(gram: str, flagged: list[str]) -> bool:
    """True if some other, shorter flagged phrase is a contiguous part of gram."""
    gram_words = gram.split()
    for other in flagged:
        other_words = other.split()
        if len(other_words) < len(gram_words) and is_subphrase(other_words, gram_words):
            return True
    return False


def is_subphrase(short_words: list[str], long_words: list[str]) -> bool:
    for start in range(len(long_words) - len(short_words) + 1):
        if long_words[start : start + len(short_words)] == short_words:
            return True
    return False


def is_skill_shaped(gram_tokens: list[str]) -> bool:
    """A single strongly-shaped token, or a title-case run with one shaped token.

    Excludes anything containing a stopword so ordinary English phrases like
    "with experience" never qualify.
    """
    if any(token.lower() in STOPWORDS for token in gram_tokens):
        return False
    if len(gram_tokens) == 1:
        return is_shaped_token(gram_tokens[0])
    looks_like_a_name = all(is_name_part(token) for token in gram_tokens)
    return looks_like_a_name and any(is_shaped_token(token) for token in gram_tokens)


def is_shaped_token(token: str) -> bool:
    """The four 'this looks like a technology' heuristics."""
    if token.lower() in DOTTED_ENGLISH:
        return False
    has_internal_caps = re.search(r"[a-z][A-Z]", token) is not None  # FastAPI, PyTorch
    is_dotted = re.search(r"[A-Za-z0-9]\.[A-Za-z0-9]", token) is not None  # Node.js
    is_acronym = re.fullmatch(r"[A-Z]{2,6}", token) is not None  # AWS, ETL, GCP
    has_tech_suffix = token.lower().endswith(TECH_SUFFIXES)
    return has_internal_caps or is_dotted or is_acronym or has_tech_suffix


def is_name_part(token: str) -> bool:
    """A token that could be part of a multi-word technology name."""
    return token[:1].isupper() or is_shaped_token(token)


def print_summary(report: AuditReport, output_path: Path) -> None:
    print(f"Scanned {report['scanned_files']} file(s).")
    if report["scanned_files"] == 0:
        print("No .txt files found — nothing to audit.")
        return
    print(f"Total skill matches: {report['total_matches']}")
    for category, count in report["matches_by_category"].items():
        print(f"  {category}: {count}")
    gaps = report["candidate_gaps"]
    print(f"\nCandidate taxonomy gaps: {len(gaps)}")
    for gap in gaps:
        print(f"  {gap['token']!r} — {gap['occurrences']}x across {len(gap['files'])} file(s)")
    print(f"\nReport written to {output_path}")


if __name__ == "__main__":
    main()
