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
    # Handle implementation_phases - can be a list of strings or a list of dicts with phase details
    implementation_phases = pj.get("implementation_phases", [])
    if isinstance(implementation_phases, list):
        # Ensure each phase is properly formatted
        phases_cleaned = []
        for phase in implementation_phases[:10]:  # Limit to 10 phases
            if isinstance(phase, dict):
                # If it's a dict, extract phase name and details
                phase_name = str(phase.get("phase", phase.get("name", ""))).strip()[:100]
                phase_details = str(phase.get("details", phase.get("description", ""))).strip()[:500]
                if phase_name:
                    phases_cleaned.append({"phase": phase_name, "details": phase_details})
            elif isinstance(phase, str):
                # If it's a string, use it as phase name
                phases_cleaned.append({"phase": str(phase).strip()[:100], "details": ""})
    else:
        phases_cleaned = []
    
    return {
        "title": str(pj.get("title", "")).strip()[:200],
        "difficulty": str(pj.get("difficulty", "")).strip()[:40],
        "estimated_time": str(pj.get("estimated_time", "")).strip()[:60],
        "description": str(pj.get("description", "")).strip()[:800],
        "key_features": clamp_list(pj.get("key_features", []), 5),
        "skills_demonstrated": clamp_list(pj.get("skills_demonstrated", []), 10),
        "tech_stack": clamp_list(pj.get("tech_stack", []), 15),
        "project_outline": str(pj.get("project_outline", "")).strip()[:500],
        "implementation_phases": phases_cleaned,
        "portfolio_impact": str(pj.get("portfolio_impact", "")).strip()[:400],
        "bonus_challenges": clamp_list(pj.get("bonus_challenges", []), 8),
    }

def enforce_top_schema(data: dict, required_gap_skills: list | None = None, primary_gap_skill: str | None = None, resume_skills: dict | None = None, paid_course_skills: set | None = None) -> dict:
    """Ensure JSON structure with 2 projects, most important listed first."""
    if not isinstance(data, dict):
        return {}
    
    # Build set of available skills from resume for Project 1 filtering
    available_skills_set = set()
    if resume_skills:
        for bucket in TARGET_BUCKETS:
            available_skills_set.update(resume_skills.get(bucket, []))
    
    # Build set of gap skills for filtering
    gap_skills_set = set(required_gap_skills) if required_gap_skills else set()
    
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
            
            # PROJECT 1 ENFORCEMENT: Remove any gap skills that shouldn't be there
            if len(projects) >= 1:
                p1 = projects[0]
                
                # Filter out gap skills from skills_demonstrated
                if gap_skills_set and available_skills_set:
                    p1_skills = p1.get("skills_demonstrated", [])
                    p1_skills_filtered = [s for s in p1_skills if s not in gap_skills_set]
                    if len(p1_skills_filtered) < len(p1_skills):
                        p1["skills_demonstrated"] = clamp_list(p1_skills_filtered, 10)
                
                # Filter out gap skills from tech_stack (check each item)
                if gap_skills_set:
                    p1_tech_stack = p1.get("tech_stack", [])
                    p1_tech_stack_filtered = []
                    for stack_item in p1_tech_stack:
                        # Check if the stack item contains any gap skills
                        contains_gap_skill = any(gap_skill.lower() in str(stack_item).lower() for gap_skill in gap_skills_set)
                        if not contains_gap_skill:
                            p1_tech_stack_filtered.append(stack_item)
                    if len(p1_tech_stack_filtered) < len(p1_tech_stack):
                        p1["tech_stack"] = clamp_list(p1_tech_stack_filtered, 15)
            
            # PROJECT 2 ENFORCEMENT: Filter to only allowed skills (resume + paid course)
            if len(projects) >= 2:
                p2 = projects[1]
                
                # Build allowed skills set for Project 2: resume skills + paid course skills
                allowed_p2_skills = available_skills_set.copy()
                if paid_course_skills:
                    allowed_p2_skills.update(paid_course_skills)
                
                # Filter skills_demonstrated to only include allowed skills
                p2_skills = p2.get("skills_demonstrated", [])
                p2_skills_filtered = [s for s in p2_skills if s in allowed_p2_skills]
                if len(p2_skills_filtered) < len(p2_skills):
                    p2["skills_demonstrated"] = clamp_list(p2_skills_filtered, 10)
                
                # Filter tech_stack to only include allowed skills
                p2_tech_stack = list(p2.get("tech_stack", []))
                p2_tech_stack_filtered = []
                for stack_item in p2_tech_stack:
                    # Check if the stack item contains any allowed skill
                    item_str = str(stack_item).lower()
                    contains_allowed_skill = any(
                        allowed_skill.lower() in item_str 
                        for allowed_skill in allowed_p2_skills
                    )
                    if contains_allowed_skill:
                        p2_tech_stack_filtered.append(stack_item)
                
                if len(p2_tech_stack_filtered) < len(p2_tech_stack):
                    p2["tech_stack"] = clamp_list(p2_tech_stack_filtered, 15)
                
                # Now ensure primary gap skill is included (if it's in allowed skills)
                if required_gap_skills and primary_gap_skill and primary_gap_skill in allowed_p2_skills:
                    # Add primary skill to the front of skills_demonstrated if not present
                    skills_demo = list(p2.get("skills_demonstrated", []))
                    if primary_gap_skill not in skills_demo:
                        skills_demo.insert(0, primary_gap_skill)
                    else:
                        # Move to front if already present
                        skills_demo.remove(primary_gap_skill)
                        skills_demo.insert(0, primary_gap_skill)
                    p2["skills_demonstrated"] = clamp_list(skills_demo, 10)
                    
                    # Also add to tech_stack if not already present
                    tech_stack_lower = [str(item).lower() for item in p2.get("tech_stack", [])]
                    primary_in_stack = any(primary_gap_skill.lower() in item.lower() for item in tech_stack_lower)
                    if not primary_in_stack:
                        p2_tech_stack = list(p2.get("tech_stack", []))
                        p2_tech_stack.insert(0, primary_gap_skill)
                        p2["tech_stack"] = clamp_list(p2_tech_stack, 15)
                    else:
                        # Move to front if already present
                        p2_tech_stack = list(p2.get("tech_stack", []))
                        for i, item in enumerate(p2_tech_stack):
                            if primary_gap_skill.lower() in str(item).lower():
                                p2_tech_stack.pop(i)
                                p2_tech_stack.insert(0, primary_gap_skill)
                                p2["tech_stack"] = clamp_list(p2_tech_stack, 15)
                                break
                
                # Add other missing skills from paid course (but primary is already handled above)
                if required_gap_skills and paid_course_skills:
                    p2_tech_stack = list(p2.get("tech_stack", []))
                    tech_stack_lower = [str(item).lower() for item in p2_tech_stack]
                    cov_set = set(p2.get("skills_demonstrated", [])) | set([item.lower() for item in p2_tech_stack])
                    
                    # Only add skills that are in paid course skills (allowed)
                    top_needed = set(required_gap_skills[:4]) & paid_course_skills  # Intersection: only skills in paid course
                    if primary_gap_skill:
                        top_needed.discard(primary_gap_skill)
                    missing_to_add = [s for s in top_needed if s.lower() not in cov_set][:3]
                    if missing_to_add:
                        # Add to tech_stack if not already present
                        for skill in missing_to_add:
                            skill_in_stack = any(skill.lower() in str(item).lower() for item in p2_tech_stack)
                            if not skill_in_stack:
                                p2_tech_stack.append(skill)
                        p2["tech_stack"] = clamp_list(p2_tech_stack, 15)
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
            md.append(f"- **Tech Stack:**")
            for item in pj.get('tech_stack', []):
                md.append(f"  - {item}")
            md.append(f"- **Portfolio Impact:** {pj['portfolio_impact']}")
            if pj['bonus_challenges']:
                md.append(f"- **Bonus Challenges:** {', '.join(pj['bonus_challenges'])}")
            md.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")

# =============== Prompt Builder ===============
def build_prompt(job_text: str, resume_skills: dict, gaps=None, primary_gap_skill: str | None = None, course_recommendations: dict | None = None):
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
            "tech_stack": ["Frontend: React", "Backend: FastAPI", "Database: PostgreSQL", "Deployment: Docker"],
            "project_outline": "Brief overview of the project structure and approach",
            "implementation_phases": [
                {
                    "phase": "Phase 1: Setup and Planning",
                    "details": "Set up development environment, create project structure, define requirements"
                },
                {
                    "phase": "Phase 2: Core Development",
                    "details": "Implement main features, build core functionality"
                },
                {
                    "phase": "Phase 3: Testing and Deployment",
                    "details": "Write tests, deploy to production, document the project"
                }
            ],
            "portfolio_impact": "Why this impresses employers",
            "bonus_challenges": ["challenge1", "challenge2"]
        }
    ]
}
""".strip()

    # Extract all available skills from resume (flat list for easy reference)
    available_skills_flat = []
    if resume_skills:
        for bucket in TARGET_BUCKETS:
            available_skills_flat.extend(resume_skills.get(bucket, []))
    available_skills_flat = sorted(set(available_skills_flat))
    
    gaps_block = "\n**Candidate Missing Required Skills (from job vs resume):**\n" + json.dumps(gaps, indent=2, ensure_ascii=False) if gaps else ""
    primary_skill_block = f"\n\n**PRIMARY MISSING SKILL (MUST be the focus of Project 2):**\n{json.dumps(primary_gap_skill, ensure_ascii=False)}" if primary_gap_skill else ""
    
    # Build available skills block for Project 1 restrictions
    available_skills_block = f"""
**CANDIDATE'S AVAILABLE SKILLS (ONLY these can be used in Project 1):**
{json.dumps(available_skills_flat, indent=2, ensure_ascii=False)}

**CRITICAL RESTRICTION FOR PROJECT 1:**
- Project 1 MUST ONLY use skills from the "Available Skills" list above.
- Project 1 MUST NOT include ANY skills from the "Missing Required Skills" list.
- If a technology, framework, or tool is NOT in the available skills list, it CANNOT be used in Project 1.
- This ensures the candidate can build Project 1 immediately with their current skillset.
- Project 1 should be creative and impressive while staying within these skill boundaries.
"""
    
    # Build course recommendations block
    course_block = ""
    paid_course_block = ""
    if course_recommendations:
        all_courses = []
        free_courses = course_recommendations.get("free_courses", [])
        paid_courses = course_recommendations.get("paid_courses", [])
        
        # Combine all courses for general reference
        all_courses.extend(free_courses)
        all_courses.extend(paid_courses)
        
        # Extract paid courses specifically for Project 2 alignment
        paid_course_skills = set()
        paid_course_summaries = []
        if paid_courses:
            for course in paid_courses[:3]:  # Focus on top 3 paid courses
                title = course.get("title", "Unknown Course")
                skills_covered = course.get("skills_covered", [])
                platform = course.get("platform", "Unknown")
                description = course.get("description", "")[:300]  # Longer description for paid courses
                link = course.get("link", "")
                paid_course_skills.update(skills_covered)
                paid_course_summaries.append({
                    "title": title,
                    "platform": platform,
                    "skills_covered": skills_covered,
                    "description": description,
                    "link": link
                })
        
        if all_courses:
            # Extract key information from all courses for general reference
            course_summaries = []
            all_course_skills = set()
            for course in all_courses[:5]:  # Limit to top 5 courses
                title = course.get("title", "Unknown Course")
                skills_covered = course.get("skills_covered", [])
                platform = course.get("platform", "Unknown")
                description = course.get("description", "")[:200]  # Truncate description
                all_course_skills.update(skills_covered)
                course_summaries.append({
                    "title": title,
                    "platform": platform,
                    "skills_covered": skills_covered,
                    "description": description
                })
            
            # Filter course skills to only include those the candidate already has (for Project 1)
            course_skills_available = [s for s in all_course_skills if s in available_skills_flat]
            course_skills_missing = [s for s in all_course_skills if s not in available_skills_flat]
            
            course_block = f"""
**RECOMMENDED COURSES (Projects MUST align with these courses):**
{json.dumps(course_summaries, indent=2, ensure_ascii=False)}

**CRITICAL REQUIREMENT - Course Alignment:**
- **For Project 1:** Only use course skills that the candidate ALREADY HAS (see "Available Course Skills" below).
- **For Project 2:** MUST sync with the PAID COURSE recommendations (see separate section below).
- Projects should serve as practical application and reinforcement of what the candidate learns in these courses.
- This ensures a cohesive learning path: courses teach the theory, projects provide hands-on practice with the same tools.

**Available Course Skills (Candidate already knows - OK for Project 1):**
{json.dumps(sorted(course_skills_available), indent=2, ensure_ascii=False) if course_skills_available else "None - candidate doesn't have any skills from recommended courses"}

**Missing Course Skills (Only for Project 2 - learning project):**
{json.dumps(sorted(course_skills_missing), indent=2, ensure_ascii=False) if course_skills_missing else "None"}
"""
        
        # Build separate block for paid courses - CRITICAL for Project 2
        if paid_course_summaries:
            # Combine available skills + paid course skills = ALLOWED skills for Project 2
            allowed_skills_p2 = sorted(set(available_skills_flat) | paid_course_skills)
            
            paid_course_block = f"""
**🎯 PAID COURSE RECOMMENDATIONS (Project 2 MUST sync with these):**
{json.dumps(paid_course_summaries, indent=2, ensure_ascii=False)}

**CRITICAL - Project 2 STRICT RESTRICTIONS:**
- Project 2 MUST be designed to work hand-in-hand with the PAID COURSE recommendations above.
- **Project 2 can ONLY use skills from TWO sources:**
  1. Skills the candidate ALREADY HAS (from resume - see "Available Skills" section above)
  2. Skills taught in the PAID COURSE recommendations (listed below)
- **Project 2 MUST NOT include ANY other skills, technologies, or frameworks that are NOT in these two lists.**
- The tech_stack for Project 2 MUST ONLY include technologies from: (resume skills) + (paid course skills)
- The project should be structured so that after completing the paid course, the candidate can immediately build this project using ONLY what they know + what they learned from the paid course.
- This creates a perfect learning-to-practice pipeline: Course → Project.

**Paid Course Skills (will be learned from the course):**
{json.dumps(sorted(list(paid_course_skills)), indent=2, ensure_ascii=False) if paid_course_skills else "None"}

**ALLOWED Skills for Project 2 (Resume Skills + Paid Course Skills ONLY):**
{json.dumps(allowed_skills_p2, indent=2, ensure_ascii=False) if allowed_skills_p2 else "None"}

**IMPORTANT:** Project 2's tech_stack, skills_demonstrated, and all technologies MUST ONLY come from the "ALLOWED Skills" list above. NO EXCEPTIONS.
"""

    return f"""
You are an expert career mentor and AI educator in 2025.
Recommend **exactly two project ideas** for the candidate below.
The projects must be in the **same core track** (e.g., MLOps, Data Science, AI Engineering),
but should be **distinct** so the student can choose one.
The most impactful and relevant project must appear **first** in the output.

**Your goals:**
- Focus on projects that fit directly with the *core* of the target job role.
- Make them realistic (20–60 hours total), portfolio-ready, and interview-worthy.
- Use the candidate's current skills while stretching them slightly.
- Ensure the first project is the highest impact and strongest match for the job description.
- **CRITICALLY IMPORTANT:** Projects MUST align with and use the same technologies/skills as the recommended courses (see course section below).

**Job Description:**
{job_text}

**Candidate Résumé Skills:**
{json.dumps(resume_skills, indent=2, ensure_ascii=False)}

{available_skills_block if available_skills_flat else ""}{gaps_block}{primary_skill_block}{course_block}{paid_course_block}

**Strict Output Format (JSON only):**
{schema_json}

**Guidelines:**
- Output must have exactly one main key (the core track, e.g., "MLOps (Marketing)").
- Under that, output exactly 2 projects (most important first).
- Each project must include all listed fields.
- Projects should highlight creativity, relevance, and measurable deliverables (GitHub repo, dashboard, API, etc.).
- **Project 1 - STRICT RESTRICTIONS (Build with Current Skills ONLY):**
  - MUST ONLY use skills from the "Available Skills" list - NO EXCEPTIONS.
  - MUST NOT include ANY missing skills, technologies, or frameworks that are not in the candidate's resume.
  - Must align with the job description and recommended courses, but ONLY using technologies the candidate already knows.
  - If a recommended course teaches a skill the candidate doesn't have, DO NOT include that skill in Project 1.
  - This project should be something the candidate can build immediately without learning new technologies.
  - Be creative within these constraints - show what's possible with their current skillset.
- **Project 2 - Learning Project (STRICT RESTRICTIONS - Resume Skills + Paid Course Skills ONLY):**
  - **CRITICAL RESTRICTION:** Project 2 can ONLY use skills from TWO sources:
    1. Skills the candidate already has (from resume - see "Available Skills" section)
    2. Skills from the PAID COURSE recommendations (see "Paid Course Skills" section)
  - **DO NOT include ANY skills, technologies, or frameworks that are NOT in the "ALLOWED Skills for Project 2" list.**
  - The project MUST use the EXACT same technologies and skills taught in the paid course(s).
  - The project should be designed so that after taking the paid course, the candidate can immediately build this project using ONLY what they know + what they learned from the paid course.
  - MUST focus on and prominently feature the PRIMARY MISSING SKILL listed above (if it's in the paid course skills).
  - The primary skill must be:
    - Listed FIRST in "skills_demonstrated" (if it's in the allowed skills list)
    - Included in "tech_stack" (preferably at the front)
    - Central to the project's description and key features
    - The main learning objective of this project
  - The tech_stack MUST ONLY include technologies from the "ALLOWED Skills for Project 2" list - nothing else.
  - The project description should reference how it applies concepts from the paid course.
  - **Remember: Only use skills from resume + paid course. Do not add extra technologies or skills.**

**IMPORTANT - New Required Fields:**
- **tech_stack**: A detailed list of the complete technology stack for the project. Include frontend, backend, database, deployment tools, etc. Format as ["Frontend: React", "Backend: FastAPI", "Database: PostgreSQL", etc.].
  - **Project 1:** tech_stack MUST only include technologies from the "Available Skills" list.
  - **Project 2:** tech_stack MUST ONLY include technologies from the "ALLOWED Skills for Project 2" list (resume skills + paid course skills). DO NOT add any technologies that are not in this list.
- **project_outline**: A brief 2-3 sentence overview of the project structure, approach, and high-level architecture.
- **implementation_phases**: A list of 3-6 implementation phases, each with:
  - **phase**: The phase name (e.g., "Phase 1: Setup and Planning")
  - **details**: Detailed breakdown of what to do in this phase, including specific tasks, technologies to use, and deliverables. Be specific and actionable.

Return only valid JSON.
""".strip()

# =============== Main ===============
def main():
    parser = argparse.ArgumentParser(description="Recommend 2 distinct but related project ideas ordered by importance.")
    parser.add_argument("--job_txt", required=True, help="Path to job_description.txt")
    parser.add_argument("--resume_skills", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--job_skills", default=None, help="Optional path to job_description_*_skills.json for required gaps enforcement")
    parser.add_argument("--primary_gap", default=None, help="Primary gap skill to focus on (same as course recommendations)")
    parser.add_argument("--courses", default=None, help="Optional path to course recommendations JSON file")
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
    
    # Load course recommendations if provided
    course_recommendations = None
    paid_course_skills_set = set()
    if args.courses:
        try:
            course_recommendations = load_json(args.courses)
            # Extract paid course skills for enforcement
            paid_courses = course_recommendations.get("paid_courses", [])
            for course in paid_courses[:3]:  # Top 3 paid courses
                skills_covered = course.get("skills_covered", [])
                paid_course_skills_set.update(skills_covered)
        except Exception as e:
            print(f"⚠️ Warning: Could not load course recommendations from {args.courses}: {e}")
            print("Continuing without course recommendations...")

    attempts = 0
    cleaned = {}
    primary_gap = args.primary_gap
    while attempts < 3:
        prompt = build_prompt(job_text, resume_skills, gaps=gaps_flat, primary_gap_skill=primary_gap, course_recommendations=course_recommendations)
        response = client.chat.completions.create(
            model="gpt-5.1",
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

        cleaned = enforce_top_schema(data, required_gap_skills=gaps_flat, primary_gap_skill=primary_gap, resume_skills=resume_skills, paid_course_skills=paid_course_skills_set if paid_course_skills_set else None)
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
