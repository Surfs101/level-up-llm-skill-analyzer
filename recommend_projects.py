# recommend_projects.py
# Generates exactly 2 distinct project ideas, ordered by importance (most relevant first).

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]
TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]

# =============== Utility Functions ===============
def load_text(p: str) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def load_json(p: str) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def get_resume_skills(resume_json: dict) -> dict:
    skills = resume_json.get("skills", {})
    return {b: sorted(set(skills.get(b, []))) for b in BUCKETS}

def get_job_required_skills(job_json: dict) -> dict:
    required = job_json.get("required", {}).get("skills", {})
    return {b: sorted(set(required.get(b, []))) for b in BUCKETS}

def compute_missing_required(resume_skills: dict, job_required: dict) -> list:
    gaps = []
    for b in TARGET_BUCKETS:
        have = set(resume_skills.get(b, []))
        need = set(job_required.get(b, []))
        gaps.extend(sorted(list(need - have)))
    return gaps

def slugify(s: str) -> str:
    s = (s or "project").lower()
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, ' ')
    return "_".join([t for t in s.split() if t])

def clamp_list(value, max_len=5):
    if not isinstance(value, list):
        return []
    return value[:max_len]

def ensure_project_shape(pj: dict) -> dict:
    return {
        "title": str(pj.get("title", "")).strip()[:200],
        "difficulty": str(pj.get("difficulty", "")).strip()[:40],
        "estimated_time": str(pj.get("estimated_time", "")).strip()[:60],
        "description": str(pj.get("description", "")).strip()[:800],
        "key_features": clamp_list(pj.get("key_features", []), 5),
        "skills_demonstrated": clamp_list(pj.get("skills_demonstrated", []), 10),
        "technologies": clamp_list(pj.get("technologies", []), 10),
        "portfolio_impact": str(pj.get("portfolio_impact", "")).strip()[:400],
        "bonus_challenges": clamp_list(pj.get("bonus_challenges", []), 8),
    }

def enforce_top_schema(data: dict, required_gap_skills: list | None = None) -> dict:
    """Ensure JSON structure with 2 projects, most important listed first."""
    if not isinstance(data, dict):
        return {}
    cleaned = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, list):
            continue
        projects = []
        for pj in v[:2]:  # two projects only
            if isinstance(pj, dict):
                projects.append(ensure_project_shape(pj))
        if projects:
            # Sort projects: the first should be the "most impactful"
            projects = sorted(projects, key=lambda x: len(x["skills_demonstrated"]), reverse=True)
            # If we have gap skills, enforce that project 2 intentionally includes them
            if required_gap_skills and len(projects) >= 2:
                top_needed = set(required_gap_skills[:4])
                p2 = projects[1]
                cov_set = set(p2.get("skills_demonstrated", [])) | set(p2.get("technologies", []))
                # If coverage is low, nudge by appending top_missing items (best-effort correction)
                missing_to_add = [s for s in required_gap_skills if s not in cov_set][:3]
                if missing_to_add:
                    p2["skills_demonstrated"] = clamp_list(list(dict.fromkeys(list(p2.get("skills_demonstrated", [])) + missing_to_add)), 10)
            cleaned[k.strip()[:80]] = projects
            break
    return cleaned

def write_outputs(obj: dict, outdir: Path, role_hint: str):
    outdir.mkdir(parents=True, exist_ok=True)
    slug = slugify(role_hint)
    json_path = outdir / f"projects_{slug}.json"
    md_path = outdir / f"projects_{slug}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    md = [f"# Project Recommendations – {role_hint}\n"]
    for core_focus, projects in obj.items():
        md.append(f"## {core_focus}\n")
        md.append("_Projects are ranked by impact and relevance (most important first)_\n")
        for i, pj in enumerate(projects, 1):
            md.append(f"### {i}. {pj['title']}")
            md.append(f"- **Difficulty:** {pj['difficulty']}")
            md.append(f"- **Estimated Time:** {pj['estimated_time']}")
            md.append(f"- **Description:** {pj['description']}")
            md.append(f"- **Key Features:** {', '.join(pj['key_features']) or '-'}")
            md.append(f"- **Skills Demonstrated:** {', '.join(pj['skills_demonstrated']) or '-'}")
            md.append(f"- **Technologies:** {', '.join(pj['technologies']) or '-'}")
            md.append(f"- **Portfolio Impact:** {pj['portfolio_impact']}")
            if pj['bonus_challenges']:
                md.append(f"- **Bonus Challenges:** {', '.join(pj['bonus_challenges'])}")
            md.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")

# =============== Prompt Builder ===============
def build_prompt(job_text: str, resume_skills: dict, gaps=None):
    schema_json = """
{
    "skill_name": [
        {
            "title": "Project Title",
            "difficulty": "Beginner/Intermediate/Advanced",
            "estimated_time": "X hours/days",
            "description": "Project description",
            "key_features": ["feature1", "feature2", "feature3"],
            "skills_demonstrated": ["skill1", "skill2", "skill3"],
            "technologies": ["tech1", "tech2", "tech3"],
            "portfolio_impact": "Why this impresses employers",
            "bonus_challenges": ["challenge1", "challenge2"]
        }
    ]
}
""".strip()

    gaps_block = "\n**Candidate Missing Required Skills (from job vs resume):**\n" + json.dumps(gaps, indent=2, ensure_ascii=False) if gaps else ""

    return f"""
You are an expert career mentor and AI educator in 2025.
Recommend **exactly two project ideas** for the candidate below.
The projects must be in the **same core track** (e.g., MLOps, Data Science, AI Engineering),
but should be **distinct** so the student can choose one.
The most impactful and relevant project must appear **first** in the output.

**Your goals:**
- Focus on projects that fit directly with the *core* of the target job role.
- Make them realistic (20–60 hours total), portfolio-ready, and interview-worthy.
- Use the candidate’s current skills while stretching them slightly.
- Ensure the first project is the highest impact and strongest match for the job description.

**Job Description:**
{job_text}

**Candidate Résumé Skills:**
{json.dumps(resume_skills, indent=2, ensure_ascii=False)}

{gaps_block}

**Strict Output Format (JSON only):**
{schema_json}

**Guidelines:**
- Output must have exactly one main key (the core track, e.g., "MLOps (Marketing)").
- Under that, output exactly 2 projects (most important first).
- Each project must include all listed fields.
- Projects should highlight creativity, relevance, and measurable deliverables (GitHub repo, dashboard, API, etc.).
- Project 1 must primarily leverage the candidate’s existing skills while aligning tightly with the job.
- Project 2 must intentionally cover the most important missing required skills (2–4 skills) from the job. Explicitly include these missing skills in "skills_demonstrated" and the plan.

Return only valid JSON.
""".strip()

# =============== Main ===============
def main():
    parser = argparse.ArgumentParser(description="Recommend 2 distinct but related project ideas ordered by importance.")
    parser.add_argument("--job_txt", required=True, help="Path to job_description.txt")
    parser.add_argument("--resume_skills", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--job_skills", default=None, help="Optional path to job_description_*_skills.json for required gaps enforcement")
    parser.add_argument("--role_hint", default="JobTrack", help="Short label for the role (e.g., 'MLOps Engineer')")
    parser.add_argument("--outdir", default="recommendations_out", help="Output directory")
    args = parser.parse_args()

    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    job_text = load_text(args.job_txt)
    resume_json = load_json(args.resume_skills)
    resume_skills = get_resume_skills(resume_json)
    job_required = load_json(args.job_skills).get("required", {}).get("skills", {}) if args.job_skills else None
    gaps_flat = compute_missing_required(resume_skills, get_job_required_skills(load_json(args.job_skills)) if args.job_skills else {b: [] for b in BUCKETS}) if args.job_skills else []

    attempts = 0
    cleaned = {}
    while attempts < 3:
        prompt = build_prompt(job_text, resume_skills, gaps=gaps_flat)
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

        cleaned = enforce_top_schema(data, required_gap_skills=gaps_flat)
        if cleaned:
            break
        attempts += 1
    if not cleaned:
        print("⚠️ No valid projects returned. Try refining the job description.")
        return

    role_hint = args.role_hint or next(iter(cleaned.keys()), "role")
    write_outputs(cleaned, Path(args.outdir), role_hint)


if __name__ == "__main__":
    main()
