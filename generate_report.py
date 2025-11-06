# generate_report.py
# Pipeline orchestrator that generates a comprehensive career matching report
# Takes resume text and job description text as inputs, returns structured report

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Import functions from existing modules
from pdf_resume_parser import PDFToTextConverter
from score_skills_match import score_match, parse_weights
from recommend_courses import (
    get_resume_skills, get_job_required_skills, get_job_preferred_skills, compute_gaps,
    build_prompt, enforce_schema_and_rules, gaps_empty, _rank_missing_skills
)
from recommend_projects import (
    get_resume_skills as get_resume_skills_projects,
    build_prompt as build_project_prompt, enforce_top_schema
)

# Load environment
load_dotenv()
BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]


def extract_skills_from_text(resume_text: str) -> dict:
    """Extract skills from resume text using OpenAI."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are an expert résumé parser.
Make sure to list only the languages and skills that are actually mentioned in the résumé.
Extract all skills from the resume text below and classify them into:
- ProgrammingLanguages
- FrameworksLibraries
- ToolsPlatforms

Output must be STRICT JSON only in this format:
{{
  "skills": {{
    "ProgrammingLanguages": ["Python", "SQL"],
    "FrameworksLibraries": ["React", "scikit-learn"],
    "ToolsPlatforms": ["Git", "Docker"],
  }}
}}

Resume:
{resume_text}
"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw = response.choices[0].message.content
    return json.loads(raw)


def extract_job_skills_from_text(job_description_text: str) -> dict:
    """Extract required/preferred skills from job description using OpenAI."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are an expert job-description parser.

Task:
1) Extract ONLY skills explicitly present in the text.
2) Split them into two groups:
   - required  = cues like "required", "must", "we need", "minimum"
   - preferred = cues like "preferred", "nice to have", "plus", "bonus"
3) Classify each group into EXACTLY these buckets:
   - ProgrammingLanguages
   - FrameworksLibraries
   - ToolsPlatforms

Return STRICT JSON ONLY in this format (no extra text):

{{
  "required": {{
    "skills": {{
      "ProgrammingLanguages": ["Python", "SQL"],
      "FrameworksLibraries": ["React", "scikit-learn"],
      "ToolsPlatforms": ["Git", "Docker"],
    }}
  }},
  "preferred": {{
    "skills": {{
      "ProgrammingLanguages": ["Java"],
      "FrameworksLibraries": ["TensorFlow"],
      "ToolsPlatforms": ["Kubernetes"],
    }}
  }}
}}

Job Description:
{job_description_text}
""".strip()
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    # Ensure schema
    out = {"required": {}, "preferred": {}}
    for side in ["required", "preferred"]:
        block = data.get(side, {}) or {}
        skills = block.get("skills", block)
        clean = {}
        for b in BUCKETS:
            v = skills.get(b, [])
            clean[b] = v if isinstance(v, list) else []
        out[side] = {"skills": clean}
    
    return out


def get_course_recommendations(resume_json: dict, job_json: dict, role: str = "Target Role") -> dict:
    """Get course recommendations based on skill gaps."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    have = get_resume_skills(resume_json)
    need_required = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need_required)
    # If no REQUIRED gaps, fall back to PREFERRED gaps
    if gaps_empty(gaps):
        need_pref = get_job_preferred_skills(job_json)
        gaps = compute_gaps(have, need_pref)
    
    prompt = build_prompt(role, gaps)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    target_skills = sorted({s for b in BUCKETS for s in gaps.get(b, [])})
    cleaned = enforce_schema_and_rules(data, target_skills)
    
    return cleaned


def get_project_recommendations(job_description_text: str, resume_json: dict, job_json: dict, primary_gap_skill: str | None = None) -> dict:
    """Get project recommendations based on job, resume, and explicit gaps.
    
    Args:
        job_description_text: Raw job description text
        resume_json: Resume skills JSON
        job_json: Job skills JSON (required/preferred)
        primary_gap_skill: Primary missing skill to focus on (same as course recommendations)
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    resume_skills = get_resume_skills_projects(resume_json)
    have = get_resume_skills(resume_json)
    need = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need)
    
    # If no required gaps, try preferred
    if gaps_empty(gaps):
        need = get_job_preferred_skills(job_json)
        gaps = compute_gaps(have, need)
    
    prompt = build_project_prompt(job_description_text, resume_skills, gaps, primary_gap_skill=primary_gap_skill)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    # Flatten required gaps to a list for enforcement (technical buckets only handled in project module)
    flat_gaps = sorted({s for b in gaps for s in gaps[b]})
    cleaned = enforce_top_schema(data, required_gap_skills=flat_gaps, primary_gap_skill=primary_gap_skill)
    return cleaned


def generate_report(
    resume_text: str,
    job_description_text: str,
    role_label: str = "Target Role",
    weights: str = "required=1.0,preferred=0.5"
) -> Dict[str, Any]:
    """
    Generate comprehensive career matching report.
    
    Args:
        resume_text: Raw text content from resume (PDF converted to text)
        job_description_text: Job description text
        role_label: Label for the role (e.g., "MLOps Engineer")
        weights: Weights string for scoring (e.g., "required=1.0,preferred=0.5")
    
    Returns:
        Dictionary containing comprehensive report with:
        - overall_score: Overall resume skill match score
        - required_skills: Match score and missing skills for required
        - preferred_skills: Match score and missing skills for preferred
        - course_recommendations: Course recommendations with all info
        - project_recommendations: Project recommendations
    """
    
    # Step 1: Extract skills from resume
    print("Step 1: Extracting skills from resume...")
    resume_skills_json = extract_skills_from_text(resume_text)
    
    # Step 2: Extract skills from job description
    print("Step 2: Extracting skills from job description...")
    job_skills_json = extract_job_skills_from_text(job_description_text)
    
    # Step 3: Score skills match
    print("Step 3: Computing skills match scores...")
    w_req, w_pref = parse_weights(weights)
    match_scores = score_match(resume_skills_json, job_skills_json, w_req, w_pref)
    
    # Step 4: Get course recommendations (and compute primary gap skill)
    print("Step 4: Generating course recommendations...")
    have = get_resume_skills(resume_skills_json)
    need_required = get_job_required_skills(job_skills_json)
    gaps = compute_gaps(have, need_required)
    # If no REQUIRED gaps, fall back to PREFERRED gaps (same logic as course recommendations)
    if gaps_empty(gaps):
        need_pref = get_job_preferred_skills(job_skills_json)
        gaps = compute_gaps(have, need_pref)
    
    # Compute primary gap skill (same as used in course recommendations)
    ranked_missing = _rank_missing_skills(gaps)
    primary_gap_skill = ranked_missing[0] if ranked_missing else None
    
    course_recommendations = get_course_recommendations(
        resume_skills_json, 
        job_skills_json, 
        role_label
    )
    
    # Step 5: Get project recommendations (sync with course recommendations via primary gap skill)
    print("Step 5: Generating project recommendations...")
    project_recommendations = get_project_recommendations(
        job_description_text,
        resume_skills_json,
        job_skills_json,
        primary_gap_skill=primary_gap_skill
    )
    
    # Compile final report
    report = {
        "overall_score": {
            "weighted_score": match_scores["summary"]["weighted_score"],
            "required_coverage_pct": match_scores["summary"]["required_coverage_pct"],
            "preferred_coverage_pct": match_scores["summary"]["preferred_coverage_pct"],
            "overall_jaccard_pct": match_scores["summary"]["overall_jaccard_pct"]
        },
        "required_skills": {
            "match_score": match_scores["summary"]["required_coverage_pct"],
            "covered_count": match_scores["summary"]["counts"]["required"]["covered"],
            "total_count": match_scores["summary"]["counts"]["required"]["total"],
            "covered_skills": match_scores["covered_skills"]["required"],
            "missing_skills": match_scores["missing_skills"]["required"]
        },
        "preferred_skills": {
            "match_score": match_scores["summary"]["preferred_coverage_pct"],
            "covered_count": match_scores["summary"]["counts"]["preferred"]["covered"],
            "total_count": match_scores["summary"]["counts"]["preferred"]["total"],
            "covered_skills": match_scores["covered_skills"]["preferred"],
            "missing_skills": match_scores["missing_skills"]["preferred"]
        },
        "course_recommendations": course_recommendations,
        "project_recommendations": project_recommendations
    }
    
    print("✅ Report generation complete!")
    return report


if __name__ == "__main__":
    # Example usage for testing
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <resume_text_file> <job_description_file> [role_label]")
        sys.exit(1)
    
    resume_file = sys.argv[1]
    job_file = sys.argv[2]
    role_label = sys.argv[3] if len(sys.argv) > 3 else "Target Role"
    
    with open(resume_file, "r", encoding="utf-8") as f:
        resume_text = f.read()
    
    with open(job_file, "r", encoding="utf-8") as f:
        job_text = f.read()
    
    report = generate_report(resume_text, job_text, role_label)
    
    # Save report
    output_file = "final_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Report saved to {output_file}")
    print(f"\nOverall Score: {report['overall_score']['weighted_score']}%")
    print(f"Required Skills Match: {report['required_skills']['match_score']}%")
    print(f"Preferred Skills Match: {report['preferred_skills']['match_score']}%")

