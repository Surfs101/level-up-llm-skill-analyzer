# Known issues

## Matcher limitations (rule-based extraction, v1)

The skill matcher (`backend/app/nlp/matcher.py`) is rule-based: it matches text
against the taxonomy's surface forms via FlashText — no fuzzy matching, no LLM,
fully deterministic and zero per-analysis cost. Two structural limitations follow
from that design. Both were measured on the real 19-pair eval corpus at F1 0.97
(`backend/tests/unit/nlp/test_matcher_eval.py`).

### 1. Implied-but-not-named skills are missed (recall floor)

The matcher only catches skills written as a recognizable surface form. Skills the
text *describes* without *naming* are missed — e.g. a resume that describes a CI
pipeline without writing "CI/CD", or says "micro-service architecture" with no
clean token, or splits "data analysis and visualization". Measured: all 11
residual false negatives on the eval corpus are this class. This is the deliberate
cost of rule-based (vs LLM) extraction chosen for determinism + zero per-analysis
cost. Mitigation: add the missing surface form to the taxonomy via
`scripts/build_taxonomy.py`; find candidates with `python -m app.nlp.audit`. NOT a
bug to "fix" in code.

### 2. Word-sense collisions need context the matcher lacks

A keyword matcher can't tell "Logistic Regression" (the ML method, a skill) from
"regression testing" (QA practice), or "iOS/Android" the dev platforms from
"iOS/Android icons" (graphic design). Measured: 4 residual false positives. Fixing
this requires context/NER, out of scope for v1. Accepted.

### Not limitations (do not "fix")

- 7 eval FPs are frozen-label gaps: the matcher correctly catches a skill the
  frozen gold labels omit. The matcher is right; the labels are frozen.
- 8 eval FPs are intentional rule-3 non-labels (incidental generic-noun prose).
