"""Matcher F1 gate for Phase 1.

Pairs each fixture <name>.txt with its <name>.expected.json (= {"skill_ids":
[...]}) under tests/fixtures/resumes and tests/fixtures/jds, runs the matcher,
and asserts micro-averaged F1 > 0.90 across all pairs.

Only the real, human-labeled corpus counts toward the gate: the glob is the two
top-level dirs (non-recursive), so the synthetic smoke corpus parked in
tests/fixtures/_synthetic/ is excluded. Files whose expected set is empty (a
low-signal fixture with no genuine skills) are skipped — they carry no F1 signal
and would only risk a divide-by-zero.

If no labeled fixtures exist yet, the test skips cleanly so CI stays green until a
labeled corpus is dropped in.
"""

import json
from pathlib import Path

import pytest

from app.nlp.matcher import extract_skill_ids

FIXTURE_DIRS = [
    Path(__file__).resolve().parents[2] / "fixtures" / "resumes",
    Path(__file__).resolve().parents[2] / "fixtures" / "jds",
]
F1_THRESHOLD = 0.90


def load_labeled_pairs() -> list[tuple[Path, set[str]]]:
    """Every .txt with a sibling .expected.json and a non-empty expected id set."""
    pairs = []
    for directory in FIXTURE_DIRS:
        for text_path in sorted(directory.glob("*.txt")):
            expected_path = text_path.with_suffix(".expected.json")
            if not expected_path.exists():
                continue
            expected = set(json.loads(expected_path.read_text())["skill_ids"])
            if not expected:
                continue  # low-signal fixture — no F1 signal, skip it
            pairs.append((text_path, expected))
    return pairs


def test_matcher_micro_f1_above_threshold() -> None:
    pairs = load_labeled_pairs()
    if not pairs:
        pytest.skip("no labeled fixtures yet — drop <name>.txt + <name>.expected.json to enable")

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    for text_path, expected in pairs:
        predicted = extract_skill_ids(text_path.read_text())
        true_positives += len(predicted & expected)
        false_positives += len(predicted - expected)
        false_negatives += len(expected - predicted)

    precision = true_positives / (true_positives + false_positives) if true_positives else 0.0
    recall = true_positives / (true_positives + false_negatives) if true_positives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    assert f1 > F1_THRESHOLD, (
        f"micro-F1 {f1:.3f} below {F1_THRESHOLD} "
        f"(precision {precision:.3f}, recall {recall:.3f}, {len(pairs)} pairs)"
    )
