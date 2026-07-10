"""Skill extraction — the single place text becomes a set of skill ids.

Both pipelines (resume/JD analysis and the jobs cron) call extract_skill_ids, so
extraction is symmetric: the same text always yields the same ids no matter which
pipeline asks. Matching is rule-based via FlashText against the taxonomy's surface
map — no fuzzy matching, no LLM, fully deterministic.

Two FlashText processors are built once at import and shared read-only:

  - the main CASE-INSENSITIVE matcher, loaded with every taxonomy surface except a
    few short forms that are precision poison in lowercase (see EXCLUDED_SURFACES);
  - a small CASE-SENSITIVE matcher (see CASE_SENSITIVE_SURFACES) that rescues those
    short forms by requiring the exact capitalization people actually write.

extract_skill_ids runs both and unions the result.
"""

import logging
import time

from flashtext import KeywordProcessor

from app.nlp.taxonomy import get_surface_to_id_map
from app.nlp.text_clean import normalize

logger = logging.getLogger(__name__)


# INCLUSION PRINCIPLE for the case-sensitive set: a surface belongs here iff it is
# a genuine skill surface that is (a) <=4 chars or a known uppercase acronym, AND
# (b) whose lowercase form is a common English word / single letter that caused or
# would cause false positives in case-insensitive matching. The key listed is the
# EXACT capitalization people write for the skill; the value is its skill id.
#
# Applying (a)+(b) to the candidates:
#   R  -> single letter, "r" is a stray-letter/subreddit fragment (FP)         [in]
#   Go -> "go" is an ubiquitous English verb ("go live", "go-to")              [in]
#   C  -> single letter, "c" matches any stray "c"                             [in]
#   AD -> "ad" = advertisement, a common word (FP'd on resume prose)           [in]
# Excluded after testing against (b):
#   D   -> no "D" language entry exists in the taxonomy (nothing to rescue).
#   TF  -> unrescuable: uppercase "TF" overwhelmingly means term-frequency
#          ("TF-IDF"), not TensorFlow, so case-sensitivity does not help. The
#          "tf" alias is dropped in build_taxonomy.py instead.
#   SAS / SSE -> their lowercase forms are NOT common English words and (FlashText
#          being word-boundary aware) never collide inside other tokens, so they
#          cause no FPs — they stay case-insensitive (strictly higher recall).
# Deliberately NOT rescued anywhere (ambiguous even uppercase):
#   AI  -> "AI" = artificial intelligence AND Adobe Illustrator; unrescuable.
#          Illustrator stays reachable via "Illustrator" only.
#   EDA -> ambiguous uppercase (exploratory data analysis vs event-driven arch).
#          event-driven-architecture must match via its full phrase.
#   ROC -> the ML metric, not the Roc language; "roc"/"ROC" dropped as a surface.
CASE_SENSITIVE_SURFACES = {
    "R": "r",
    "Go": "go",
    "C": "c",
    "AD": "microsoft-active-directory",
}

# Surfaces removed from the CASE-INSENSITIVE matcher. The lowercase forms of every
# case-sensitive surface go here (so e.g. lowercase "go" no longer fires), plus two
# entries reachable only via their compound aliases because the bare word is prose
# poison in either case: "less" (Less CSS -> "less css"/"lesscss") and "roc" (the
# Roc language -> "roc lang"; bare "roc"/"ROC" means the ROC/AUC metric).
EXCLUDED_SURFACES = {surface.lower() for surface in CASE_SENSITIVE_SURFACES} | {"less", "roc"}


def build_keyword_processor() -> KeywordProcessor:
    """Load taxonomy surfaces into a case-insensitive FlashText trie.

    add_keyword(surface_form, skill_id) makes a match return the canonical id
    rather than the matched text, so extraction is normalized for free. FlashText
    handles longest-match and word boundaries itself, including names with . / + #
    such as Node.js, C++, and C#. Surfaces in EXCLUDED_SURFACES are skipped — they
    are matched case-sensitively (or not at all) instead.
    """
    keyword_processor = KeywordProcessor(case_sensitive=False)
    for surface_form, skill_id in get_surface_to_id_map().items():
        if surface_form in EXCLUDED_SURFACES:
            continue
        keyword_processor.add_keyword(surface_form, skill_id)
    return keyword_processor


def build_case_sensitive_processor() -> KeywordProcessor:
    """Load the curated CASE_SENSITIVE_SURFACES into a case-sensitive FlashText trie.

    "#", "+", and "&" are registered as non-word-boundaries so a one-letter surface
    sitting next to one is treated as part of a larger token, not a match: "C#" and
    "C++" must NOT yield C, and "R&D" must NOT yield R. ("-" and "." are left as
    boundaries so "Go-based" and a sentence-final "Go." still match.)
    """
    keyword_processor = KeywordProcessor(case_sensitive=True)
    for boundary_char in "#+&":
        keyword_processor.add_non_word_boundary(boundary_char)
    for surface_form, skill_id in CASE_SENSITIVE_SURFACES.items():
        keyword_processor.add_keyword(surface_form, skill_id)
    return keyword_processor


_build_start = time.perf_counter()
_keyword_processor = build_keyword_processor()
_ci_build_ms = (time.perf_counter() - _build_start) * 1000

_build_start = time.perf_counter()
_case_sensitive_processor = build_case_sensitive_processor()
_cs_build_ms = (time.perf_counter() - _build_start) * 1000

KEYWORD_COUNT = len(get_surface_to_id_map())
BUILD_MS = _ci_build_ms + _cs_build_ms

logger.info(
    "matcher ready: %d case-insensitive keywords in %.1f ms + %d case-sensitive in %.1f ms",
    KEYWORD_COUNT,
    _ci_build_ms,
    len(CASE_SENSITIVE_SURFACES),
    _cs_build_ms,
)


def _is_js_file_suffix(cleaned: str, start: int, end: int) -> bool:
    """True when this match is the ".js" tail of a framework name, not the JS skill.

    FlashText treats "." as a word boundary, so the bare "js" alias matches the
    ".js" suffix of an unmapped framework ("D3.js" -> a spurious javascript hit).
    A standalone "JS" ("HTML / CSS / JS") is preceded by whitespace, not a dot, so
    only the dot-preceded case is rejected.
    """
    return cleaned[start:end].lower() == "js" and start > 0 and cleaned[start - 1] == "."


def extract_skill_ids(text: str) -> set[str]:
    """Return the set of canonical skill ids found in the text.

    The input is normalized first so unicode noise does not cause misses. Both the
    case-insensitive and case-sensitive matchers run over the same cleaned text and
    their ids are unioned. The result is always canonical ids — never surface forms
    or aliases — and is deduped because it is a set.
    """
    cleaned = normalize(text)
    ids = {
        skill_id
        for skill_id, start, end in _keyword_processor.extract_keywords(cleaned, span_info=True)
        if not _is_js_file_suffix(cleaned, start, end)
    }
    ids.update(_case_sensitive_processor.extract_keywords(cleaned))
    return ids
