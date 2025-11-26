# recommend_projects.py
# Generates exactly 2 distinct project ideas, ordered by importance (most relevant first).
# Uses only JSON skills (no raw resume text).

import os
import json
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Import shared normalization
from skill_normalization import BUCKETS

TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]

# =============== Utility Functions ===============
def load_text(p: str) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def load_json(p: str) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

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
    # Handle implementation_phases - now a list of dicts with phase and outline
    implementation_phases = pj.get("implementation_phases", [])
    if isinstance(implementation_phases, list):
        phases_cleaned = []
        for phase in implementation_phases[:5]:  # Limit to 5 phases
            if isinstance(phase, dict):
                # New format: dict with "phase" and "outline"
                phase_name = str(phase.get("phase", phase.get("name", ""))).strip()[:200]
                phase_outline = str(phase.get("outline", phase.get("details", ""))).strip()[:2000]  # Increased limit for detailed step-by-step instructions
                if phase_name:
                    phases_cleaned.append({
                        "phase": phase_name,
                        "outline": phase_outline
                    })
            elif isinstance(phase, str):
                # Backward compatibility: if string format, convert to dict
                phases_cleaned.append({
                    "phase": str(phase).strip()[:200],
                    "outline": ""
                })
    else:
        phases_cleaned = []
    
    return {
        "title": str(pj.get("title", "")).strip()[:200],
        "description": str(pj.get("description", "")).strip()[:800],
        "tech_stack": clamp_list(pj.get("tech_stack", []), 15),
        "implementation_phases": phases_cleaned,
    }

def enforce_top_schema(data: dict, required_gap_skills: list | None = None, primary_gap_skill: str | None = None, resume_skills: dict | None = None, paid_course_skills: set | None = None) -> dict:
    """
    Ensure JSON structure with 2 projects, most important listed first.
    
    Note: required_gap_skills and primary_gap_skill are kept in signature for backward compatibility
    but are no longer used in the implementation.
    """
    if not isinstance(data, dict):
        return {}
    
    # Build set of available skills from resume for Project 1 filtering (once, at start)
    available_skills_set = set()
    if resume_skills:
        # Handle both dict (with any bucket keys) and list (flat) formats
        if isinstance(resume_skills, dict):
            # Iterate over all values in dict (works with any bucket structure)
            for bucket_skills in resume_skills.values():
                if isinstance(bucket_skills, list):
                    available_skills_set.update(bucket_skills)
        elif isinstance(resume_skills, list):
            # If it's a flat list, use it directly
            available_skills_set.update(resume_skills)
    
    # Pre-compute lowercase set for Project 1 tech_stack filtering (compute once, not in loop)
    available_skills_lower = {s.lower() for s in available_skills_set} if available_skills_set else set()
    
    cleaned = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, list):
            continue
        projects = []
        for pj in v[:2]:  # two projects only
            if isinstance(pj, dict):
                projects.append(ensure_project_shape(pj))
        if projects:
            # Sort projects: trust LLM order, but sort by tech_stack length as a tiebreaker
            projects = sorted(projects, key=lambda x: len(x.get("tech_stack", [])), reverse=True)
            
            # PROJECT 1 ENFORCEMENT: Filter tech_stack to only use available skills
            if len(projects) >= 1:
                p1 = projects[0]
                
                # Filter tech_stack to only include available skills (single pass)
                if available_skills_lower:
                    p1_tech_stack = p1.get("tech_stack", [])
                    p1_tech_stack_filtered = []
                    for stack_item in p1_tech_stack:
                        item_lower = str(stack_item).lower()
                        # Check if any available skill substring exists in item
                        if any(skill in item_lower for skill in available_skills_lower):
                            p1_tech_stack_filtered.append(stack_item)
                    if len(p1_tech_stack_filtered) < len(p1_tech_stack):
                        p1["tech_stack"] = clamp_list(p1_tech_stack_filtered, 15)
            
            # PROJECT 2 ENFORCEMENT: Filter tech_stack to only allowed skills (resume + paid course)
            if len(projects) >= 2:
                p2 = projects[1]
                
                # Build allowed skills set for Project 2: resume skills + paid course skills
                allowed_p2_skills = available_skills_set.copy()
                if paid_course_skills:
                    allowed_p2_skills.update(paid_course_skills)
                
                # Pre-compute lowercase allowed skills for faster matching (once)
                allowed_p2_skills_lower = {s.lower() for s in allowed_p2_skills} if allowed_p2_skills else set()
                
                # Filter tech_stack to only include allowed skills (single pass)
                if allowed_p2_skills_lower:
                    p2_tech_stack = p2.get("tech_stack", [])
                    p2_tech_stack_filtered = []
                    for stack_item in p2_tech_stack:
                        item_lower = str(stack_item).lower()
                        # Check if any allowed skill substring exists in item
                        if any(skill in item_lower for skill in allowed_p2_skills_lower):
                            p2_tech_stack_filtered.append(stack_item)
                    if len(p2_tech_stack_filtered) < len(p2_tech_stack):
                        p2["tech_stack"] = clamp_list(p2_tech_stack_filtered, 15)
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
            md.append(f"- **Description:** {pj['description']}")
            md.append(f"- **Tech Stack:**")
            for item in pj.get('tech_stack', []):
                md.append(f"  - {item}")
            md.append(f"- **Implementation Phases:**")
            for phase_item in pj.get('implementation_phases', []):
                if isinstance(phase_item, dict):
                    md.append(f"  - **{phase_item.get('phase', 'Phase')}:** {phase_item.get('outline', '')}")
                else:
                    md.append(f"  - {phase_item}")
            md.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")

# =============== Simplified Prompt Builder (Skills Only) ===============
def build_prompt_from_skills(
    job_text: str | None,
    available_skills_flat: list[str],
    paid_course_skills: list[str] | None,
    role_label: str
) -> str:
    """
    Build project recommendation prompt using only flattened skills lists.
    No gaps, no course_recommendations dict, no resume_skills dict.
    
    Args:
        job_text: Job description text (optional, for context)
        available_skills_flat: Flattened list of candidate's skills from resume (TARGET_BUCKETS only)
        paid_course_skills: List of skills taught by the paid course (from skills_covered field)
        role_label: Role label for context
    
    Returns:
        Complete prompt string for LLM
    """
    schema_json = """
{
    "skill_name": [
        {
            "title": "Project Title",
            "description": "2-3 sentence description of the project",
            "tech_stack": ["React", "FastAPI", "PostgreSQL"],
            "implementation_phases": [
                {
                    "phase": "Phase 1: Phase Name",
                    "outline": "Step 1: [Action] using [Skill/Technology]. Step 2: [Action] using [Skill/Technology]. Step 3: [Action] using [Skill/Technology]."
                },
                {
                    "phase": "Phase 2: Phase Name",
                    "outline": "Step 1: [Action] using [Skill/Technology]. Step 2: [Action] using [Skill/Technology]. Step 3: [Action] using [Skill/Technology]."
                },
                {
                    "phase": "Phase 3: Phase Name",
                    "outline": "Step 1: [Action] using [Skill/Technology]. Step 2: [Action] using [Skill/Technology]. Step 3: [Action] using [Skill/Technology]."
                }
            ]
        }
    ]
}
""".strip()
    
    # Build available skills block for Project 1 restrictions
    available_skills_block = f"""
**CANDIDATE'S AVAILABLE SKILLS (ONLY these can be used in Project 1):**
{json.dumps(available_skills_flat, indent=2, ensure_ascii=False)}

**CRITICAL RESTRICTION FOR PROJECT 1:**
- Project 1 MUST ONLY use skills from the "Available Skills" list above.
- If a technology, framework, or tool is NOT in the available skills list, it CANNOT be used in Project 1.
- This ensures the candidate can build Project 1 immediately with their current skillset.
- Project 1 should be creative and impressive while staying within these skill boundaries.
"""
    
    # Build Project 2 restrictions block
    paid_course_skills_list = paid_course_skills or []
    allowed_skills_p2 = sorted(set(available_skills_flat) | set(paid_course_skills_list))
    
    paid_course_skills_block = ""
    if paid_course_skills_list:
        paid_course_skills_block = f"""
**🎯 PAID COURSE SKILLS (Skills that will be learned from the paid course):**
{json.dumps(sorted(paid_course_skills_list), indent=2, ensure_ascii=False)}

**CRITICAL - Project 2 STRICT RESTRICTIONS:**
- Project 2 MUST be designed to work hand-in-hand with the paid course that teaches these skills.
- **Project 2 can ONLY use skills from TWO sources:**
  1. Skills the candidate ALREADY HAS (from resume - see "Available Skills" section above)
  2. Skills taught in the PAID COURSE (listed above)
- **Project 2 MUST NOT include ANY other skills, technologies, or frameworks that are NOT in these two lists.**
- The tech_stack for Project 2 MUST ONLY include technologies from: (resume skills) + (paid course skills)
- The project should be structured so that after completing the paid course, the candidate can immediately build this project using ONLY what they know + what they learned from the paid course.
- This creates a perfect learning-to-practice pipeline: Course → Project.

**ALLOWED Skills for Project 2 (Resume Skills + Paid Course Skills ONLY):**
{json.dumps(allowed_skills_p2, indent=2, ensure_ascii=False)}

**IMPORTANT:** Project 2's tech_stack and all technologies MUST ONLY come from the "ALLOWED Skills for Project 2" list above. NO EXCEPTIONS.
"""
    
    job_text_block = f"""
**Job Description:**
{job_text if job_text else "Not provided"}
"""
    
    job_tailoring_block = f"""
**🎯 CRITICAL - JOB DESCRIPTION TAILORING REQUIREMENT:**
The projects MUST be directly tailored to the job description's specific domain, industry, company type, and functionality.

**How to tailor projects:**
1. **Analyze the job description carefully:**
   - What industry/domain is the company in? (e.g., sports, healthcare, finance, e-commerce, education)
   - What does the company do? (e.g., sports analytics platform, healthcare data management, fintech payments)
   - What are the specific problems/challenges mentioned in the job description?
   - What technologies or systems are mentioned as being used by the company?

2. **Create domain-specific projects:**
   - If the job is at a **sports company** that does analytics/player tracking → Projects should be sports-related (e.g., "Player Performance Analytics Dashboard", "Game Statistics API")
   - If the job is at a **healthcare company** that manages patient data → Projects should be healthcare-related (e.g., "Patient Data Management System", "Medical Records API")
   - If the job is at a **fintech company** that does payments → Projects should be finance/payment-related (e.g., "Payment Processing System", "Transaction Analytics Dashboard")
   - If the job is at an **e-commerce company** → Projects should be e-commerce-related (e.g., "Product Recommendation Engine", "Order Management System")

3. **Projects must demonstrate understanding of the job's context:**
   - The project title, description, and features should clearly show it's designed for the specific industry/domain
   - The project should solve problems similar to what the company faces
   - The project should use technologies relevant to the company's tech stack (within skill constraints)
   - The project should be something that would impress THIS SPECIFIC COMPANY, not just any company

**Examples of good tailoring:**
- Job: "Sports Analytics Platform Developer" → Project: "Real-time Sports Statistics Dashboard" ✅
- Job: "Healthcare Data Engineer" → Project: "Patient Health Records Management System" ✅
- Job: "Fintech Backend Developer" → Project: "Secure Payment Transaction API" ✅

**Examples of BAD tailoring (too generic):**
- Job: "Sports Analytics Platform Developer" → Project: "Generic Web Dashboard" ❌
- Job: "Healthcare Data Engineer" → Project: "Todo List App" ❌
- Job: "Fintech Backend Developer" → Project: "Blog API" ❌

**REMEMBER:** Both Project 1 and Project 2 must be tailored to the job description's domain, even though they have different skill constraints.
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
- **CRITICALLY IMPORTANT:** Projects MUST be tailored to the job description's specific domain, industry, and company type (see detailed instructions below).

{job_text_block}

{job_tailoring_block}

{available_skills_block}

{paid_course_skills_block}

**Strict Output Format (JSON only):**
{schema_json}

**Guidelines:**
- Output must have exactly one main key (the core track, e.g., "MLOps (Marketing)" or "Sports Analytics Platform").
- Under that, output exactly 2 projects (most important first).
- Each project must include all listed fields.
- Projects should highlight creativity, relevance, and measurable deliverables (GitHub repo, dashboard, API, etc.).
- **BOTH PROJECTS MUST BE TAILORED TO THE JOB DESCRIPTION:**
  - Analyze the job description to identify the industry, domain, company type, and specific problems they solve.
  - Create projects that are directly relevant to that domain (e.g., sports projects for sports companies, healthcare projects for healthcare companies).
  - The project title, description, and features should clearly demonstrate understanding of the job's context.
  - Generic projects that could apply to any company are NOT acceptable - they must be domain-specific.
- **Project 1 - STRICT RESTRICTIONS (Build with Current Skills ONLY):**
  - MUST ONLY use skills from the "Available Skills" list - NO EXCEPTIONS.
  - MUST NOT include ANY skills, technologies, or frameworks that are not in the candidate's resume.
  - This project should be something the candidate can build immediately without learning new technologies.
  - **MUST be tailored to the job description's domain/industry** (e.g., if it's a sports company, make it sports-related).
  - Be creative within these constraints - show what's possible with their current skillset while staying relevant to the job.
- **Project 2 - Learning Project (STRICT RESTRICTIONS - Resume Skills + Paid Course Skills ONLY):**
  - **CRITICAL RESTRICTION:** Project 2 can ONLY use skills from TWO sources:
    1. Skills the candidate already has (from resume - see "Available Skills" section)
    2. Skills from the PAID COURSE (see "Paid Course Skills" section)
  - **DO NOT include ANY skills, technologies, or frameworks that are NOT in the "ALLOWED Skills for Project 2" list.**
  - The project MUST use the EXACT same technologies and skills taught in the paid course.
  - The project should be designed so that after taking the paid course, the candidate can immediately build this project using ONLY what they know + what they learned from the paid course.
  - The tech_stack MUST ONLY include technologies from the "ALLOWED Skills for Project 2" list - nothing else.
  - The project description should reference how it applies concepts from the paid course.
  - **MUST be tailored to the job description's domain/industry** (e.g., if it's a sports company, make it sports-related, even when using paid course skills).
  - **Remember: Only use skills from resume + paid course. Do not add extra technologies or skills.**

**IMPORTANT - Required Fields (with brevity limits):**
- **description**: Maximum 2-3 sentences. Use technical, precise language. Focus on architecture, implementation approach, and technical objectives. Avoid casual or overly simple explanations.
- **tech_stack**: Maximum 6 items. Format as ["React", "FastAPI", "PostgreSQL", etc.]. List only the core technologies using their official names.
  - **Project 1:** tech_stack MUST only include technologies from the "Available Skills" list.
  - **Project 2:** tech_stack MUST ONLY include technologies from the "ALLOWED Skills for Project 2" list (resume skills + paid course skills). DO NOT add any technologies that are not in this list.
- **implementation_phases**: Exactly 3 phases, each with:
  - **phase**: The phase name using technical terminology (e.g., "Phase 1: Infrastructure Setup and Environment Configuration")
  - **outline**: A detailed, step-by-step outline that is easy to follow. For each step, clearly state:
    1. What to do (specific action)
    2. Which skill/technology to use (explicitly name the skill from tech_stack)
    3. When to use it (in what context or order)
    4. How to use it (brief implementation guidance)
    Format as clear, numbered steps. Example: "Step 1: Set up the project structure using [React] by running 'npx create-react-app'. Step 2: Configure the API client using [FastAPI] to create endpoints. Step 3: Connect to the database using [PostgreSQL] by installing psycopg2 and creating connection strings."
    Make it easy for students to follow - each step should be actionable and clearly indicate which skill from the tech_stack is being applied.

**CRITICAL - Language Requirements:**
- Use technical, professional terminology throughout (e.g., "implement RESTful API endpoints" not "make an API", "configure container orchestration" not "set up Docker")
- Reference specific technologies, frameworks, and tools by their official names
- Describe implementation details using industry-standard terminology
- Keep all text concise. Do NOT write long paragraphs.

Return only valid JSON.
""".strip()


# =============== Main Recommendation Function ===============
def recommend_projects_from_skills(
    resume_skills_json: dict,
    paid_course_skills: list[str] | None,
    job_description_text: str | None,
    role_label: str,
) -> dict:
    """
    Generate project recommendations using only JSON skills (no raw resume text).
    
    Project 1: Uses only candidate's existing skills from resume_skills_json.
    Project 2: Uses candidate's existing skills + skills from paid course.
    
    Args:
        resume_skills_json: Resume skills JSON with structure {"skills": {bucket: [skills]}}
        paid_course_skills: List of skills taught by the paid course (from skills_covered field)
        job_description_text: Job description text (optional, for context only)
        role_label: Role label for context
    
    Returns:
        Dictionary with project recommendations: {"projects": {...}}
    """
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Get resume skills (now a flat list, no buckets)
    resume_skills_list = resume_skills_json.get("skills", []) or []
    if not isinstance(resume_skills_list, list):
        resume_skills_list = []
    available_skills_flat = sorted(set(resume_skills_list))
    
    # Build prompt using only flattened skills lists
    prompt = build_prompt_from_skills(
        job_text=job_description_text,
        available_skills_flat=available_skills_flat,
        paid_course_skills=paid_course_skills,
        role_label=role_label
    )
    
    # Call OpenAI once
    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more technical, precise language
        )
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            raise Exception(f"OpenAI API quota exceeded. Please check your billing and plan. Error: {error_msg}")
        else:
            raise Exception(f"Error calling OpenAI API for project recommendations: {error_msg}")
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    # Use enforce_top_schema with:
    # - required_gap_skills=None (no gap filtering)
    # - primary_gap_skill=None (no primary skill enforcement)
    # - resume_skills=flat list converted to dict format for enforcement (for Project 1 filtering)
    # - paid_course_skills=set(paid_course_skills or []) (for Project 2 filtering)
    # Convert flat list to dict format for enforce_top_schema (it still expects bucket structure for filtering)
    # Since we don't know which bucket each skill belongs to, put all skills in FrameworksLibraries bucket
    # (this is just for filtering, the actual bucket doesn't matter for enforcement)
    resume_skills_for_enforcement = {"FrameworksLibraries": available_skills_flat}
    cleaned = enforce_top_schema(
        data,
        required_gap_skills=None,
        primary_gap_skill=None,
        resume_skills=resume_skills_for_enforcement,
        paid_course_skills=set(paid_course_skills or []) if paid_course_skills else None
    )
    
    return cleaned


# =============== Public function for generate_report.py orchestrator ===============
def get_project_recommendations(
    resume_skills_json: dict,
    job_description_text: str,
    course_recommendations: Optional[dict],
    role_label: str = "Target Role"
) -> dict:
    """
    Get project recommendations based on resume skills and paid course skills.
    
    This is a thin wrapper that extracts paid_course_skills from course_recommendations
    and calls recommend_projects_from_skills().
    
    Args:
        resume_skills_json: Resume skills JSON with structure {"skills": [list]}
        job_description_text: Raw job description text (for context)
        course_recommendations: Course recommendations dict (from get_course_recommendations_with_fallback)
        role_label: Role label for context
    
    Returns:
        Dictionary with project recommendations: {"projects": {...}}
    """
    # Extract paid_course_skills from first paid course
    paid_course_skills = None
    if course_recommendations:
        paid_courses = course_recommendations.get("paid_courses", [])
        if paid_courses:
            first_paid = paid_courses[0]
            paid_course_skills = first_paid.get("skills_covered", []) or []
            print(f"Debug: Extracted {len(paid_course_skills)} skills from first paid course: {paid_course_skills[:5]}...")
    
    # Call recommend_projects_from_skills
    project_recommendations = recommend_projects_from_skills(
        resume_skills_json=resume_skills_json,
        paid_course_skills=paid_course_skills,
        job_description_text=job_description_text,
        role_label=role_label,
    )
    
    return project_recommendations


# =============== CLI Main ===============
def main():
    parser = argparse.ArgumentParser(description="Recommend 2 distinct but related project ideas ordered by importance.")
    parser.add_argument("--job_txt", required=True, help="Path to job_description.txt")
    parser.add_argument("--resume_skills", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--courses", default=None, help="Optional path to course recommendations JSON file")
    parser.add_argument("--role_hint", default="JobTrack", help="Short label for the role (e.g., 'MLOps Engineer')")
    parser.add_argument("--outdir", default="recommendations_out", help="Output directory")
    args = parser.parse_args()

    # Load files
    job_text = load_text(args.job_txt)
    resume_json = load_json(args.resume_skills)
    
    # Extract paid course skills if courses file provided
    paid_course_skills = None
    if args.courses:
        try:
            course_recommendations = load_json(args.courses)
            paid_courses = course_recommendations.get("paid_courses", [])
            if paid_courses:
                paid_course_skills = paid_courses[0].get("skills_covered", []) or []
        except Exception as e:
            print(f"⚠️ Warning: Could not load course recommendations from {args.courses}: {e}")
            print("Continuing without course recommendations...")
    
    # Use the new function instead of making a separate GPT call
    cleaned = recommend_projects_from_skills(
        resume_skills_json=resume_json,
        paid_course_skills=paid_course_skills,
        job_description_text=job_text,
        role_label=args.role_hint
    )
    
    if not cleaned:
        print("⚠️ No valid projects returned. Try refining the job description.")
        return

    role_hint = args.role_hint or next(iter(cleaned.keys()), "role")
    write_outputs(cleaned, Path(args.outdir), role_hint)


if __name__ == "__main__":
    main()
