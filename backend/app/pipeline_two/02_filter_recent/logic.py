"""Step 02 logic — keep recent US/Canada postings (design §9 step 2).

Two filters, both must pass:
  - Recency: updated within the last 21 days (matches the purge window in step 5).
  - Location: a US or Canada signal in the location string — a full state/province
    name, a country marker, a "City, ST" two-letter code, or a remote-US/CA flag.

The location check is a deliberate heuristic (Greenhouse location strings are free
text). A posting with no location gives no signal, so it's dropped.
"""

import re
from datetime import UTC, datetime, timedelta

from app.greenhouse.client import GreenhousePosting

from .schemas import FilterResult

RECENT_DAYS = 21

_US_STATES = [
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia",
]
_CA_PROVINCES = [
    "alberta",
    "british columbia",
    "manitoba",
    "new brunswick",
    "newfoundland and labrador",
    "nova scotia",
    "ontario",
    "prince edward island",
    "quebec",
    "saskatchewan",
    "northwest territories",
    "nunavut",
    "yukon",
]
_COUNTRY_AND_REMOTE_MARKERS = [
    "united states of america",
    "united states",
    "u.s.a.",
    "u.s.",
    "usa",
    "north america",
    "canada",
    "remote - us",
    "remote us",
    "us remote",
    "remote, us",
    "remote (us",
    "remote - united states",
    "remote - canada",
    "remote canada",
    "remote - north america",
]
# Substring markers we can match cheaply (state/province names rarely appear inside
# unrelated words in a location field).
_NAME_MARKERS = _US_STATES + _CA_PROVINCES + _COUNTRY_AND_REMOTE_MARKERS

_STATE_CODES = [
    "al",
    "ak",
    "az",
    "ar",
    "ca",
    "co",
    "ct",
    "de",
    "fl",
    "ga",
    "hi",
    "id",
    "il",
    "in",
    "ia",
    "ks",
    "ky",
    "la",
    "me",
    "md",
    "ma",
    "mi",
    "mn",
    "ms",
    "mo",
    "mt",
    "ne",
    "nv",
    "nh",
    "nj",
    "nm",
    "ny",
    "nc",
    "nd",
    "oh",
    "ok",
    "or",
    "pa",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "vt",
    "va",
    "wa",
    "wv",
    "wi",
    "wy",
    "dc",
    "ab",
    "bc",
    "mb",
    "nb",
    "nl",
    "ns",
    "on",
    "pe",
    "qc",
    "sk",
    "nt",
    "nu",
    "yt",
]
# A "City, ST" style code, e.g. "San Francisco, CA" or "Toronto, ON".
_CODE_PATTERN = re.compile(r",\s*(" + "|".join(_STATE_CODES) + r")\b", re.IGNORECASE)


def filter_recent(postings: list[GreenhousePosting], now: datetime | None = None) -> FilterResult:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=RECENT_DAYS)
    kept = [
        posting
        for posting in postings
        if posting.updated_at >= cutoff and is_us_or_canada(posting.location)
    ]
    return FilterResult(filtered=kept)


def is_us_or_canada(location: str | None) -> bool:
    if not location:
        return False
    lowered = location.lower()
    if any(marker in lowered for marker in _NAME_MARKERS):
        return True
    return bool(_CODE_PATTERN.search(location))
