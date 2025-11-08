# recommend_courses.py
# EXACTLY 2 recommendations: one FREE and one PAID (DeepLearning.AI, Udemy, Coursera only)

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]
PLATFORM_WHITELIST = {"DeepLearning.AI", "Udemy", "Coursera"}
# Course recommendations should ignore soft skills entirely
TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]
# Importance weights per bucket (higher → more important for gap closure)
BUCKET_WEIGHTS = {
    "ToolsPlatforms": 1.0,
    "FrameworksLibraries": 0.9,
    "ProgrammingLanguages": 0.8,
    "SoftSkills": 0.3,
}


# ---------- utils ----------
def load_json(p: str):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def get_resume_skills(resume_json: dict):
    skills = resume_json.get("skills", {})
    return {b: set(skills.get(b, [])) for b in TARGET_BUCKETS}

def get_job_required_skills(job_json: dict):
    required = job_json.get("required", {}).get("skills", {})
    return {b: set(required.get(b, [])) for b in TARGET_BUCKETS}

def get_job_preferred_skills(job_json: dict):
    preferred = job_json.get("preferred", {}).get("skills", {})
    return {b: set(preferred.get(b, [])) for b in TARGET_BUCKETS}

def compute_gaps(have: dict, need: dict):
    return {b: sorted(list(need[b] - have[b])) for b in TARGET_BUCKETS}


def _rank_missing_skills(gaps: dict) -> list:
    """Rank missing skills by bucket importance and alphabetical as tiebreaker."""
    scored = []
    for b in TARGET_BUCKETS:
        for s in gaps.get(b, []) or []:
            scored.append((-(BUCKET_WEIGHTS.get(b, 0.5)), s.lower(), s))
    scored.sort()
    return [orig for _, __, orig in scored]

def gaps_empty(gaps: dict):
    return all(len(v) == 0 for v in gaps.values())

def is_price(s: str) -> bool:
    return isinstance(s, str) and s.startswith("$") and any(ch.isdigit() for ch in s)

def normalize_link(v):
    if v is None:
        return None
    if isinstance(v, str) and (v.startswith("http") or v == ""):
        return v
    return None

def clamp_to_target(skills_list, target_set):
    if not isinstance(skills_list, list):
        return []
    return sorted([s for s in skills_list if s in target_set])

def compute_coverage(target_set, free_courses, paid_courses):
    coverage = {s: [] for s in target_set}
    def add_course(course):
        title = (course.get("title") or "").strip()
        for s in course.get("skills_covered", []):
            if s in coverage and title and title not in coverage[s]:
                coverage[s].append(title)
    for c in free_courses: add_course(c)
    for c in paid_courses: add_course(c)
    covered = {s for s, lst in coverage.items() if lst}
    uncovered = sorted(list(set(target_set) - covered))
    pct = round(100 * len(covered) / max(1, len(target_set)))
    return coverage, uncovered, pct


# ---------- prompt ----------
def build_prompt(role: str, gaps: dict, primary_gap_skill: str | None = None, ranked_missing: list | None = None, job_text: str | None = None):
    target_skills = sorted({s for b in TARGET_BUCKETS for s in gaps.get(b, [])})
    if ranked_missing is None:
        ranked_missing = _rank_missing_skills(gaps)
    if primary_gap_skill is None:
        primary_gap_skill = (ranked_missing[0] if ranked_missing else (target_skills[0] if target_skills else ""))
    schema_block = """
{
    "free_courses": [
        {
            "title": "Course Title",
            "platform": "DeepLearning.AI|Udemy|Coursera",
            "skills_covered": ["skill1", "skill2", "skill3"],
            "additional_skills": ["bonus_skill1", "bonus_skill2"],
            "duration": "X weeks/hours",
            "difficulty": "Beginner|Intermediate|Advanced",
            "description": "3-4 sentences about what the course covers",
            "why_efficient": "Explain how it covers multiple target skills effectively",
            "cost": "Free|Free with paid certificate option",
            "link": "URL or null"
        }
    ],
    "paid_courses": [
        {
            "title": "Course Title",
            "platform": "DeepLearning.AI|Udemy|Coursera",
            "skills_covered": ["skill1", "skill2", "skill3"],
            "additional_skills": ["bonus_skill1", "bonus_skill2"],
            "duration": "X weeks/hours",
            "difficulty": "Beginner|Intermediate|Advanced",
            "description": "3-4 sentences about what the course covers",
            "why_efficient": "Explain how it covers multiple target skills effectively",
            "cost": "$XX.XX",
            "link": "URL or null"
        }
    ],
    "skill_coverage": {
        "skill_name": ["Course 1", "Course 2"]
    },
    "uncovered_skills": ["skill1", "skill2"],
    "coverage_percentage": 85
}
""".strip()

    return f"""
You are an expert course curator for candidates applying to the role: {role}.

INPUT (skills to close):
These are the REQUIRED skill gaps to cover (by bucket):
{json.dumps(gaps, indent=2, ensure_ascii=False)}

Flattened target skills list (only these count for coverage):
{json.dumps(target_skills, indent=2, ensure_ascii=False)}

Ranked importance of missing skills (most important first):
{json.dumps(ranked_missing, indent=2, ensure_ascii=False)}

Primary skill to close immediately (MUST be covered by BOTH courses):
{json.dumps(primary_gap_skill, ensure_ascii=False)}

Additional context from the job description (if provided):
{(job_text or '').strip()}

HARD CONSTRAINTS
- Recommend courses ONLY from: DeepLearning.AI, Udemy, Coursera.
- Return EXACTLY TWO recommendations total:
  - free_courses: array of EXACTLY 1 item (Free or "Free with paid certificate option")
  - paid_courses: array of EXACTLY 1 item (must have a price like "$49.99")
- Each course must cover as MANY target skills as possible (skills_covered ⊆ target list).
- Put any bonus coverage in additional_skills.
- Prefer end-to-end, project-based, up-to-date programs from reputable instructors.
- If you don't know the exact link, output "link": null (do NOT invent).
- Maximize overall coverage of the target skills with these two items.
- The field "skills_covered" for BOTH courses MUST include the primary skill {primary_gap_skill!s}.
- Prioritize covering the first 3 skills in the ranked list above.

OUTPUT
Return STRICT JSON ONLY in EXACTLY this structure (no extra text, no markdown). Use the schema literally:
{schema_block}

POST CONDITIONS
- "platform" ∈ {{"DeepLearning.AI","Udemy","Coursera"}}.
- free_courses length = 1 with cost ∈ {{"Free","Free with paid certificate option"}}.
- paid_courses length = 1 with cost like "$XX.XX".
- "skills_covered" only includes items from the target list.
- "skill_coverage" maps each target skill → titles that cover it.
- "uncovered_skills" lists any target skills not covered by either course.
- "coverage_percentage" = round(100 * covered_target_skills / total_target_skills).
""".strip()


# ---------- guards ----------
def enforce_schema_and_rules(data: dict, target_skills: list, primary_gap_skill: str | None = None):
    free_courses = data.get("free_courses", []) or []
    paid_courses = data.get("paid_courses", []) or []
    target_set = set(target_skills)

    def clean_course(c: dict, is_free: bool):
        c = dict(c or {})
        # platform whitelist
        plat = c.get("platform", "")
        c["platform"] = plat if plat in PLATFORM_WHITELIST else ""
        # skills_covered clamp
        c["skills_covered"] = clamp_to_target(c.get("skills_covered", []), target_set)
        # additional_skills list
        add = c.get("additional_skills", [])
        c["additional_skills"] = add if isinstance(add, list) else []
        # strings
        c["duration"] = c.get("duration", "")
        c["difficulty"] = c.get("difficulty", "")
        c["description"] = (c.get("description") or "")[:1200]
        c["why_efficient"] = (c.get("why_efficient") or "")[:600]
        c["title"] = (c.get("title") or "").strip()
        # link normalization
        c["link"] = normalize_link(c.get("link"))
        # cost rules
        cost = c.get("cost", "")
        if is_free:
            if cost not in ("Free", "Free with paid certificate option"):
                c["cost"] = "Free"
        else:
            if not is_price(cost):
                c["cost"] = "$0.00"
        return c

    free_courses = [clean_course(c, True) for c in free_courses]
    paid_courses = [clean_course(c, False) for c in paid_courses]

    # enforce EXACTLY one each by trimming extras (keep the first)
    if len(free_courses) > 1:
        free_courses = free_courses[:1]
    if len(paid_courses) > 1:
        paid_courses = paid_courses[:1]

    # ensure primary skill is covered by both items if provided
    missing_primary = False
    if primary_gap_skill:
        p = primary_gap_skill
        if not (free_courses and (p in (free_courses[0].get("skills_covered", []) or []))):
            missing_primary = True
        if not (paid_courses and (p in (paid_courses[0].get("skills_covered", []) or []))):
            missing_primary = True

    # compute coverage
    skill_coverage, uncovered_skills, coverage_percentage = compute_coverage(set(target_skills), free_courses, paid_courses)

    return {
        "free_courses": free_courses,
        "paid_courses": paid_courses,
        "skill_coverage": skill_coverage,
        "uncovered_skills": uncovered_skills,
        "coverage_percentage": coverage_percentage,
        "_violations": {"missing_primary": missing_primary}
    }


# ---------- output ----------
def dict_to_md_table(d: dict):
    if not d:
        return "_None_"
    lines = ["| Key | Value |", "|---|---|"]
    for k, v in d.items():
        if isinstance(v, list):
            v_str = ", ".join(v) if v else "-"
        elif isinstance(v, dict):
            inner = ", ".join(f"{ik}:{len(iv) if isinstance(iv, list) else str(iv)}" for ik, iv in v.items())
            v_str = inner or "-"
        else:
            v_str = str(v)
        lines.append(f"| {k} | {v_str} |")
    return "\n".join(lines)

def write_outputs(role: str, gaps: dict, data: dict, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    role_slug = role.lower().replace(" ", "_")
    json_path = outdir / f"recommendations_{role_slug}.json"
    md_path = outdir / f"recommendations_{role_slug}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    md = []
    md.append(f"# {role} – Course Recommendations (1 Free, 1 Paid)\n")
    md.append("## Required Skill Gaps (by bucket)\n")
    md.append(dict_to_md_table(gaps))

    md.append("\n\n## Free Course\n")
    if data.get("free_courses"):
        c = data["free_courses"][0]
        md.extend([
            f"- **Title:** {c['title']}",
            f"- **Platform:** {c['platform']}",
            f"- **Skills Covered:** {', '.join(c.get('skills_covered', [])) or '-'}",
            f"- **Additional Skills:** {', '.join(c.get('additional_skills', [])) or '-'}",
            f"- **Duration:** {c['duration']}",
            f"- **Difficulty:** {c['difficulty']}",
            f"- **Cost:** {c['cost']}",
            f"- **Link:** {c['link'] or '—'}",
            f"- **Why Efficient:** {c['why_efficient']}",
            f"{c['description']}",
        ])
    else:
        md.append("_None_")

    md.append("\n\n## Paid Course\n")
    if data.get("paid_courses"):
        c = data["paid_courses"][0]
        md.extend([
            f"- **Title:** {c['title']}",
            f"- **Platform:** {c['platform']}",
            f"- **Skills Covered:** {', '.join(c.get('skills_covered', [])) or '-'}",
            f"- **Additional Skills:** {', '.join(c.get('additional_skills', [])) or '-'}",
            f"- **Duration:** {c['duration']}",
            f"- **Difficulty:** {c['difficulty']}",
            f"- **Cost:** {c['cost']}",
            f"- **Link:** {c['link'] or '—'}",
            f"- **Why Efficient:** {c['why_efficient']}",
            f"{c['description']}",
        ])
    else:
        md.append("_None_")

    md.append("\n\n## Skill Coverage Map\n")
    md.append(dict_to_md_table(data.get("skill_coverage", {})))

    md.append("\n\n## Uncovered Skills\n")
    if data.get("uncovered_skills"):
        md.append(", ".join(data["uncovered_skills"]))
    else:
        md.append("_All target skills covered_")

    md.append(f"\n\n## Coverage Percentage\n**{data.get('coverage_percentage', 0)}%**\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")


# ---------- main ----------
def main():
    parser = argparse.ArgumentParser(description="Two-course recommender (exactly 1 free + 1 paid)")
    parser.add_argument("--resume", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--job", required=True, help="Path to job_description_*_skills.json")
    parser.add_argument("--role", required=True, help='Target role (e.g., "MLOps Engineer")')
    parser.add_argument("--outdir", default="recommendations_out", help="Output directory")
    parser.add_argument("--job_txt", default=None, help="Optional job_description.txt for richer context")
    args = parser.parse_args()

    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    resume_json = load_json(args.resume)
    job_json = load_json(args.job)

    have = get_resume_skills(resume_json)
    need = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need)

    if gaps_empty(gaps):
        print("🎉 No REQUIRED gaps detected. Continuing to produce a sharpening path anyway.")

    ranked_missing = _rank_missing_skills(gaps)
    target_skills = sorted({s for b in TARGET_BUCKETS for s in gaps.get(b, [])})
    target_skills = sorted({s for b in TARGET_BUCKETS for s in gaps.get(b, [])})
    primary_gap = ranked_missing[0] if ranked_missing else (target_skills[0] if target_skills else "")

    # Retry loop to enforce primary skill coverage
    attempts = 0
    cleaned = None
    while attempts < 3:
        jd_text = None
        if args.job_txt and os.path.exists(args.job_txt):
            try:
                with open(args.job_txt, "r", encoding="utf-8") as f:
                    jd_text = f.read()
            except Exception:
                jd_text = None

        prompt = build_prompt(args.role, gaps, primary_gap_skill=primary_gap, ranked_missing=ranked_missing, job_text=jd_text)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("⚠️ JSON decoding failed. Raw response:")
            print(raw)
            attempts += 1
            continue

        cleaned = enforce_schema_and_rules(data, target_skills, primary_gap_skill=primary_gap)
        if not cleaned.get("_violations", {}).get("missing_primary", False):
            break
        attempts += 1

    # Hard check: exactly 1 in each section; if not, warn so you can re-run
    if len(cleaned.get("free_courses", [])) != 1 or len(cleaned.get("paid_courses", [])) != 1:
        print("⚠️ Constraint not met: need EXACTLY 1 free and 1 paid course. "
              "Consider re-running to let the model satisfy constraints.")
    if cleaned.get("_violations", {}).get("missing_primary", False):
        print(f"⚠️ Primary gap skill '{primary_gap}' not covered by both courses. Results may be suboptimal.")

    cleaned.pop("_violations", None)
    write_outputs(args.role, gaps, cleaned, Path(args.outdir))


if __name__ == "__main__":
    main()
