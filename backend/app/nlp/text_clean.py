"""Normalize raw resume/JD text before skill matching.

FlashText matches exact characters (case-insensitive), so stray unicode — smart
quotes, em-dashes, and zero-width spaces pasted out of PDFs and web pages — can
split a keyword ("Java​Script") or glue tokens together and cause misses. We
fold those down to plain ASCII and collapse whitespace.

We deliberately KEEP the characters . / + # because they are part of real skill
names: Node.js, A/B testing, C++, C#. Stripping them would break matching.
"""

# Each unicode character maps to its plain-ASCII equivalent. Zero-width and BOM
# characters map to "" so they vanish without leaving a gap inside a word.
_CHARACTER_REPLACEMENTS = {
    "‘": "'",  # left single quote
    "’": "'",  # right single quote / apostrophe
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "–": "-",  # en dash
    "—": "-",  # em dash
    " ": " ",  # non-breaking space
    "​": "",  # zero-width space
    "‌": "",  # zero-width non-joiner
    "‍": "",  # zero-width joiner
    "﻿": "",  # byte-order mark
}


def normalize(text: str) -> str:
    """Fold non-ASCII punctuation to ASCII and collapse runs of whitespace."""
    for original, replacement in _CHARACTER_REPLACEMENTS.items():
        text = text.replace(original, replacement)
    # split() on no args splits on any whitespace run and drops empty pieces, so
    # joining with single spaces collapses tabs/newlines/multiple spaces at once.
    return " ".join(text.split())
