"""Parse the DeepLearning.AI course catalogue from a saved HTML page.

OFFLINE tooling. This is a PURE PARSER — no network, no Playwright. The live site
is behind a Cloudflare managed challenge that only clears for a real human on a
residential IP, so a human saves the fully-rendered listing page into
scrapers/input/ and this script turns it into structured course rows.

The page is a Next.js App Router app: there is no <script id="__NEXT_DATA__">.
Instead the data is streamed as a series of `self.__next_f.push([n, "<chunk>"])`
calls whose chunks, concatenated and JSON-unescaped, form the React Query
dehydrated state. Inside it each course is an object keyed by "courseId" with
slug / name / description / type and a nested "wpData" holding courseLevel.

Output: scrapers/output/deeplearning_ai_courses.json — a list of
{external_id, title, description, url, level, duration_hours}.
"""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SCRAPERS_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = SCRAPERS_DIR / "input"
DEFAULT_OUTPUT = SCRAPERS_DIR / "output" / "deeplearning_ai_courses.json"

COURSE_URL_BASE = "https://www.deeplearning.ai/courses"
# Both listing types are real courses; "course" is the long ones, "short_course"
# the majority. Other courseId objects (e.g. specializations) are skipped.
COURSE_TYPES = {"course", "short_course"}

# Captures the JSON-escaped string argument of each self.__next_f.push([n, "..."]).
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[\d+,\s*("(?:[^"\\]|\\.)*")\]\)')


@dataclass
class CourseRecord:
    external_id: str
    title: str
    description: str | None
    url: str
    level: str | None
    duration_hours: float | None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records, skipped = parse_input_dir(args.input_dir)
    write_output(records, args.output)
    print_summary(records, skipped, args.output)


def parse_input_dir(input_dir: Path) -> tuple[list[CourseRecord], int]:
    """Parse every *.html in the directory, deduping courses by slug across files."""
    html_files = sorted(input_dir.glob("*.html"))
    if not html_files:
        raise SystemExit(f"no .html files found in {input_dir} — save the listing page there first")

    by_slug: dict[str, CourseRecord] = {}
    skipped = 0
    for path in html_files:
        records, file_skipped = extract_courses(path.read_text(encoding="utf-8"))
        skipped += file_skipped
        for record in records:
            by_slug[record.external_id] = record  # later file wins on duplicate slug
    return list(by_slug.values()), skipped


def extract_courses(html: str) -> tuple[list[CourseRecord], int]:
    """Pull course records out of one saved page's __next_f payload."""
    payload = decode_next_f_payload(html)
    records: list[CourseRecord] = []
    skipped = 0
    for match in re.finditer(r'\{"courseId":', payload):
        obj_text = _balanced_object(payload, match.start())
        if obj_text is None:
            skipped += 1
            continue
        try:
            obj = json.loads(obj_text)
        except json.JSONDecodeError:
            skipped += 1
            continue
        record = _to_record(obj)
        if record is None:
            skipped += 1
            continue
        records.append(record)
    return records, skipped


def decode_next_f_payload(html: str) -> str:
    """Concatenate and JSON-unescape every __next_f push chunk into one string."""
    return "".join(json.loads(chunk) for chunk in _PUSH_RE.findall(html))


def _to_record(obj: dict) -> CourseRecord | None:
    """Map one parsed JSON course object to our output shape, or None to skip it."""
    if obj.get("type") not in COURSE_TYPES:
        return None
    slug = obj.get("slug")
    name = obj.get("name")
    if not slug or not name:
        return None

    description = (obj.get("description") or "").strip() or None
    wp_data = obj.get("wpData") or {}
    level = wp_data.get("courseLevel")
    return CourseRecord(
        external_id=slug,
        title=name,
        description=description,
        url=f"{COURSE_URL_BASE}/{slug}",
        level=level.lower() if level else None,  # 'beginner' | 'intermediate' | 'advanced'
        duration_hours=_parse_duration(wp_data.get("courseDuration")),
    )


def _parse_duration(raw: object) -> float | None:
    """The listing leaves duration null; parse a number if a future page has one."""
    if raw is None:
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _balanced_object(text: str, start: int) -> str | None:
    """Return the JSON object beginning at text[start]=='{' via brace matching.

    A flat regex can't capture these objects because they nest (wpData), so we scan
    forward tracking brace depth while ignoring braces inside strings.
    """
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def write_output(records: list[CourseRecord], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(record) for record in records]
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(records: list[CourseRecord], skipped: int, output: Path) -> None:
    with_level = sum(1 for r in records if r.level)
    with_duration = sum(1 for r in records if r.duration_hours is not None)
    total = len(records)
    print(f"parsed {total} courses -> {output}")
    print(f"  skipped (non-course / unparseable courseId objects): {skipped}")
    print(f"  with level: {with_level}/{total} | with duration: {with_duration}/{total}")
    print("  3 sample records:")
    for record in records[:3]:
        print("    " + json.dumps(asdict(record), ensure_ascii=False))


if __name__ == "__main__":
    main()
