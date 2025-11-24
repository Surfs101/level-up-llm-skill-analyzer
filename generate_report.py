# generate_report.py
# Pipeline orchestrator that generates a comprehensive career matching report
# Takes resume text and job description text as inputs, returns structured report

import os
import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

# Import functions from existing modules
from pdf_resume_parser import PDFToTextConverter
from score_skills_match import score_match, parse_weights
from extract_skills import extract_resume_skills_from_text as extract_resume_skills
from extract_job_skills import extract_job_skills_from_text as extract_job_skills_base
from recommend_courses import (
    get_resume_skills,
    get_job_required_skills,
    get_job_preferred_skills,
    compute_gaps,
    gaps_empty,
    recommend_courses_from_gaps,
    recommend_courses_for_job_skills,
    TARGET_BUCKETS,
    BUCKET_WEIGHTS,
)
from recommend_projects import (
    get_resume_skills as get_resume_skills_projects,
    build_prompt as build_project_prompt, enforce_top_schema
)

# Import shared normalization
from skill_normalization import (
    BUCKETS,
    canonicalize_skills_by_bucket,
    canonicalize_skill_name,
    normalize_to_full_form_for_output,
)

# Load environment
load_dotenv()

CRITICAL_DOMAIN_PATTERNS = {
    "Software Engineering": [
        r"software\s+engineering",
        r"software\s+engineer",
        r"software\s+developer",
        r"software\s+development",
        r"\bswe\b",
    ],
    "Machine Learning": [
        r"machine\s+learning",
        r"\bml\b",
        r"machine[-\s]?learing",
    ],
    "Artificial Intelligence": [
        r"artificial\s+intelligence",
        r"\bai\b",
    ],
    "Data Science": [
        r"data\s+science",
        r"data\s+scientist",
    ],
    "Large Language Models": [
        r"\bllm\b",
        r"large\s+language\s+model",
        r"large\s+language\s+models",
    ],
    "Retrieval-Augmented Generation": [
        r"\brag\b",
        r"retrieval-augmented\s+generation",
    ],
    "Agentic AI": [
        r"agentic\s+ai",
        r"ai\s+agency",
    ],
}


# canonicalize_skill_name and canonicalize_skills_by_bucket are now imported from skill_normalization


def filter_non_recommendable_skills(skills_dict: dict) -> dict:
    """
    Remove skills that cannot be recommended (practices, methodologies, concepts).
    Only keep concrete, learnable technical skills.
    """
    if not isinstance(skills_dict, dict):
        return skills_dict
    
    # List of non-recommendable terms (case-insensitive matching)
    non_recommendable = {
        # Practices/Methodologies
        "ci/cd", "cicd", "ci/cd pipelines", "continuous integration", "continuous deployment",
        "automated testing", "testing", "monitoring", "observability", "alerting",
        "drift detection", "version control", "agile", "scrum", "devops practices",
        # Concepts/Techniques
        "rag", "retrieval-augmented generation", "agentic ai", "mcp", "model context protocol",
        "prompt engineering", "fine-tuning", "transfer learning",
        # Generic/Abstract terms
        "best practices", "software development", "problem solving", "troubleshooting",
        "code review", "documentation", "api design", "system design",
        # Soft skills (if any slip through)
        "communication", "collaboration", "leadership", "teamwork"
    }
    
    filtered = {}
    for bucket, skills_list in skills_dict.items():
        if not isinstance(skills_list, list):
            filtered[bucket] = skills_list
            continue
        
        filtered_skills = []
        for skill in skills_list:
            if not skill:
                continue
            skill_lower = str(skill).lower().strip()
            # Check if skill is in non-recommendable list
            if skill_lower not in non_recommendable:
                # Also check if it's a substring match (e.g., "CI/CD pipelines" contains "ci/cd")
                is_non_recommendable = False
                for non_rec in non_recommendable:
                    if non_rec in skill_lower or skill_lower in non_rec:
                        is_non_recommendable = True
                        break
                
                if not is_non_recommendable:
                    filtered_skills.append(skill)
        
        filtered[bucket] = filtered_skills
    
    return filtered


def ensure_single_letter_languages(job_text: str, required_skills: dict, preferred_skills: dict):
    """
    Post-process extracted skills to ensure single-letter languages like "C" 
    are included if they appear in the job description text.
    This is a safety net in case the LLM misses them.
    Note: R is NOT auto-added - it must be explicitly extracted.
    """
    SINGLE_LETTER_LANGS = {"c": "C"}
    
    # Get all currently extracted skills (normalized to lowercase)
    extracted_skills = set()
    for bucket in BUCKETS:
        for skill_list in [required_skills.get(bucket, []), preferred_skills.get(bucket, [])]:
            for skill in skill_list:
                if skill:
                    extracted_skills.add(str(skill).lower().strip())
    
    # Check if single-letter languages appear in the job text
    for lang_lower, lang_upper in SINGLE_LETTER_LANGS.items():
        # Check if the language is mentioned in the text but not in extracted skills
        if lang_lower not in extracted_skills:
            # Use regex to find "R" or "C" as standalone words or in comma-separated lists
            # Pattern: word boundary OR comma/space before, word boundary OR comma/space after
            pattern = rf"(?<![A-Za-z0-9]){re.escape(lang_upper)}(?![A-Za-z0-9])|(?<=[, ]){re.escape(lang_upper)}(?=[, ])|(?<=,){re.escape(lang_upper)}(?=\s|,|$)|(?<=\s){re.escape(lang_upper)}(?=,|\s|$)"
            if re.search(pattern, job_text, re.IGNORECASE):
                # Add to ProgrammingLanguages bucket in required skills (prioritize required)
                if "ProgrammingLanguages" not in required_skills:
                    required_skills["ProgrammingLanguages"] = []
                # Only add if not already present (case-insensitive check)
                existing_lower = [s.lower() for s in required_skills["ProgrammingLanguages"]]
                if lang_lower not in existing_lower:
                    # Use canonicalize_skill_name to ensure proper casing
                    canonical = canonicalize_skill_name(lang_upper)
                    required_skills["ProgrammingLanguages"].append(canonical)


def ensure_critical_domains_in_skills(text: str, skills_dict: dict):
    if not text or not isinstance(skills_dict, dict):
        return
    
    target_bucket = "FrameworksLibraries"
    skills_dict.setdefault(target_bucket, [])
    bucket_list = skills_dict[target_bucket]
    
    for canonical, patterns in CRITICAL_DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                # Use canonicalize_skill_name to ensure proper casing
                canonicalized = canonicalize_skill_name(canonical)
                if canonicalized not in bucket_list:
                    bucket_list.append(canonicalized)
                break


def extract_skills_from_text(resume_text: str) -> dict:
    """
    Extract skills from resume text using the shared extraction function.
    LLM handles all matching and normalization, no post-processing needed.
    """
    # Use the shared extraction function from extract_skills.py
    return extract_resume_skills(resume_text)


def extract_job_skills_from_text(job_description_text: str) -> dict:
    """
    Extract required/preferred skills from job description using the shared extraction function.
    LLM handles all matching and normalization, no post-processing needed.
    """
    # Use the shared extraction function from extract_job_skills.py
    # Deduplication is already handled in extract_job_skills.py
    return extract_job_skills_base(job_description_text)


def get_course_recommendations(missing_skills_data: dict, job_json: dict, role: str = "Target Role", match_scores: dict = None) -> dict:
    """
    Get course recommendations with the following priority:

    1) **Missing-skill-based** (primary): recommend courses to close concrete gaps.
    2) **Job-based fallback**: if there are no courses for the missing skills
       (e.g., no "Tableau" course), recommend courses based on the job's core
       skills/domain (e.g., "Data Analysis", "Machine Learning").
    3) If neither path finds anything, return empty course lists.
    
    Returns at most 1 free course and 1 paid course.
    
    Args:
        missing_skills_data: Dictionary containing gaps and skill_weights from score_match
        job_json: Job skills JSON (for fallback)
        role: Target role name
        match_scores: Full match_scores dict (for accessing pre-ranked missing skills)
    """
    gaps = missing_skills_data.get("gaps", {})
    skill_weights_dict = missing_skills_data.get("skill_weights", {})
    
    # Use required gaps first, fall back to preferred if no required gaps
    gaps_to_use = gaps.get("required", {})
    skill_weights_to_use = skill_weights_dict.get("required", {})
    
    if not any(gaps_to_use.values()):
        gaps_to_use = gaps.get("preferred", {})
        skill_weights_to_use = skill_weights_dict.get("preferred", {})
    
    # Use pre-ranked missing skills from match_scores (already ranked by priority)
    if match_scores:
        missing_required = match_scores.get("missing_skills", {}).get("required", [])
        missing_preferred = match_scores.get("missing_skills", {}).get("preferred", [])
        ranked_skills = missing_required if any(gaps.get("required", {}).values()) else missing_preferred
    else:
        # Fallback: rank by weights (shouldn't happen if match_scores is passed)
        all_missing_skills = []
        for bucket in TARGET_BUCKETS:
            all_missing_skills.extend(gaps_to_use.get(bucket, []))
        ranked_skills = sorted(all_missing_skills, key=lambda s: skill_weights_to_use.get(s, 0.5), reverse=True)
    
    # First: try based on missing skills (gaps) - get 1 paid course initially
    # Pass ranked_skills to preserve priority order for course recommendations
    recommendations = recommend_courses_from_gaps(
        missing_skills_data=missing_skills_data,
        role=role,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1,
        ranked_skills=ranked_skills  # Pass priority-ranked skills to preserve order
    )

    free_courses = recommendations.get("free_courses") or []
    paid_courses = recommendations.get("paid_courses") or []

    # Update local variables to match recommendations (in case they were modified)
    paid_courses = recommendations.get("paid_courses", paid_courses)
    free_courses = recommendations.get("free_courses", free_courses)
    
    # If we found at least one course, return the recommendations
    if free_courses or paid_courses:
        print(f"Debug: Returning recommendations with {len(free_courses)} free and {len(paid_courses)} paid courses")
        return recommendations

    # Second: FALLBACK – recommend based on job/domain skills (job title core)
    job_required_skills = (job_json.get("required", {}) or {}).get("skills", {}) or {}
    job_preferred_skills = (job_json.get("preferred", {}) or {}).get("skills", {}) or {}

    # Build a prioritized list of job-domain skills:
    #   1) FrameworksLibraries (often domain terms like "Data Science", "Machine Learning")
    #   2) ToolsPlatforms
    #   3) ProgrammingLanguages
    job_skill_order = ["FrameworksLibraries", "ToolsPlatforms", "ProgrammingLanguages"]
    job_skill_list = []
    seen = set()

    for bucket in job_skill_order:
        for source in (job_required_skills, job_preferred_skills):
            for skill in source.get(bucket, []) or []:
                key = str(skill).strip().lower()
                if key and key not in seen:
                    job_skill_list.append(str(skill).strip())
                    seen.add(key)

    # If there are no job skills to fall back on, return empty as-is
    if not job_skill_list:
        return recommendations

    fallback_recommendations = recommend_courses_for_job_skills(
        job_skills=job_skill_list,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1,
    )

    return fallback_recommendations


def select_primary_course_skill(resume_json: dict, course_recommendations: dict | None) -> str | None:
    """
    Pick the primary learning skill for Project 2 based on the PAID course skills.
    
    Rule:
    - Look at the first paid course (we only keep 1 paid course in recommendations).
    - Flatten the candidate's current resume skills into a set.
    - Compute which skills from the course are NOT yet in the resume.
    - If there are missing course skills, return the first one.
    - Otherwise, if skills_covered is non-empty, return the first skill_covered.
    - If there is no paid course or no skills_covered, return None.
    
    Args:
        resume_json: Resume skills JSON
        course_recommendations: Course recommendations dict
    
    Returns:
        Primary learning skill from the paid course, or None if not available
    """
    if not course_recommendations:
        return None
    
    paid_courses = course_recommendations.get("paid_courses", [])
    if not paid_courses:
        return None
    
    # Get first paid course
    first_paid_course = paid_courses[0]
    skills_covered = first_paid_course.get("skills_covered", [])
    
    if not skills_covered:
        return None
    
    # Flatten all resume skills into a set (across all buckets)
    resume_skills_set = set()
    resume_skills_dict = resume_json.get("skills", {}) or {}
    for bucket in TARGET_BUCKETS:
        for skill in resume_skills_dict.get(bucket, []):
            if skill:
                resume_skills_set.add(str(skill).lower().strip())
    
    # Find skills from course that are NOT in resume
    missing_course_skills = [
        s for s in skills_covered
        if s and str(s).lower().strip() not in resume_skills_set
    ]
    
    # Return first missing course skill, or first course skill if all are covered
    if missing_course_skills:
        return missing_course_skills[0]
    elif skills_covered:
        return skills_covered[0]
    
    return None


def get_project_recommendations(job_description_text: str, resume_json: dict, job_json: dict, primary_gap_skill: str | None = None, course_recommendations: dict | None = None, match_scores: dict = None) -> dict:
    """Get project recommendations based on job, resume, explicit gaps, and course recommendations.
    
    CRITICAL: Projects MUST sync with course recommendations - Project 2 focuses on skills taught in the paid course.
    The primary_gap_skill should be the primary learning skill from the paid course (not just top missing job skill).
    
    Args:
        job_description_text: Raw job description text
        resume_json: Resume skills JSON
        job_json: Job skills JSON (required/preferred)
        primary_gap_skill: Primary learning skill from paid course to focus on (preferred over job-based gap skill)
        course_recommendations: Course recommendations dict (from get_course_recommendations) to align projects with
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    resume_skills = get_resume_skills_projects(resume_json)
    have = get_resume_skills(resume_json)
    
    # Use gaps from match_scores (LLM already handled smart matching and ranking)
    if match_scores:
        # Use gaps from match_scores (already computed, no need to recompute)
        gaps_from_match = match_scores.get("gaps", {})
        # Use required gaps, fall back to preferred
        if any(gaps_from_match.get("required", {}).values()):
            gaps = gaps_from_match.get("required", {})
        else:
            gaps = gaps_from_match.get("preferred", {})
        # Convert to dict format expected by build_prompt
        gaps = {bucket: gaps.get(bucket, []) for bucket in TARGET_BUCKETS}
        print(f"Debug: Using gaps from match_scores: {sum(len(v) for v in gaps.values())} missing skills")
    else:
        # Fallback: compute gaps independently (shouldn't happen if match_scores is passed)
        need = get_job_required_skills(job_json)
        gaps = compute_gaps(have, need)
        
        # If no required gaps, try preferred
        if gaps_empty(gaps):
            need = get_job_preferred_skills(job_json)
            gaps = compute_gaps(have, need)
        print(f"Debug: Using independently computed gaps (no course sync): {sum(len(v) for v in gaps.values())} missing skills")
    
    prompt = build_project_prompt(job_description_text, resume_skills, gaps, primary_gap_skill=primary_gap_skill, course_recommendations=course_recommendations)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            raise Exception(f"OpenAI API quota exceeded. Please check your billing and plan. Error: {error_msg}")
        else:
            raise Exception(f"Error calling OpenAI API: {error_msg}")
    
    raw = response.choices[0].message.content
    data = json.loads(raw)
    
    # Extract paid course skills for enforcement
    paid_course_skills_set = set()
    if course_recommendations:
        paid_courses = course_recommendations.get("paid_courses", [])
        for course in paid_courses[:3]:  # Top 3 paid courses
            skills_covered = course.get("skills_covered", [])
            paid_course_skills_set.update(skills_covered)
    
    # Flatten required gaps to a list for enforcement (technical buckets only handled in project module)
    flat_gaps = sorted({s for b in gaps for s in gaps[b]})
    cleaned = enforce_top_schema(data, required_gap_skills=flat_gaps, primary_gap_skill=primary_gap_skill, resume_skills=resume_skills, paid_course_skills=paid_course_skills_set if paid_course_skills_set else None)
    return cleaned


def generate_report(
    resume_text: str,
    job_description_text: str,
    role_label: str = "Target Role",
    weights: str = "required=1.0,preferred=0.5",
    progress_callback=None
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
    step_msg = "Extracting skills from resume..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    resume_skills_json = extract_skills_from_text(resume_text)
    
    # Step 2: Extract skills from job description
    step_msg = "Extracting skills from job description..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    job_skills_json = extract_job_skills_from_text(job_description_text)
    
    # Step 3: Score skills match (includes gap computation and priority analysis)
    step_msg = "Computing skills match scores and analyzing skill priorities..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    w_req, w_pref = parse_weights(weights)
    match_scores = score_match(resume_skills_json, job_skills_json, w_req, w_pref, job_description_text)
    
    # Extract gaps and skill_weights from match_scores (weights are already calculated)
    gaps = match_scores.get("gaps", {})
    skill_weights = match_scores.get("skill_weights", {})
    missing_skills_data = {
        "gaps": gaps,
        "skill_weights": skill_weights  # Pre-calculated final weights ready to use
    }
    
    # Compute primary gap skill from ranked missing skills
    missing_required = match_scores.get("missing_skills", {}).get("required", [])
    missing_preferred = match_scores.get("missing_skills", {}).get("preferred", [])
    primary_gap_skill = missing_required[0] if missing_required else (missing_preferred[0] if missing_preferred else None)
    
    # Step 4: Get course recommendations
    step_msg = "Generating course recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    
    course_recommendations = get_course_recommendations(
        missing_skills_data,
        job_skills_json,
        role_label,
        match_scores  # Pass match_scores to avoid recomputing ranked skills
    )
    
    # Step 5: Get project recommendations (sync with course recommendations - Project 2 focuses on paid course skills)
    step_msg = "Generating project recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    
    # Select primary learning skill from paid course (preferred over job-based gap skill)
    primary_course_skill = select_primary_course_skill(resume_skills_json, course_recommendations)
    
    # Use course-based primary skill if available, otherwise fall back to job-based gap skill
    primary_skill_for_projects = primary_course_skill or primary_gap_skill
    if primary_course_skill:
        print(f"Debug: Using primary learning skill from paid course: {primary_course_skill}")
    elif primary_gap_skill:
        print(f"Debug: Using job-based primary gap skill (no paid course skill available): {primary_gap_skill}")
    
    project_recommendations = get_project_recommendations(
        job_description_text,
        resume_skills_json,
        job_skills_json,
        primary_gap_skill=primary_skill_for_projects,  # Use course-based skill if available
        course_recommendations=course_recommendations,  # Pass course recommendations to align projects
        match_scores=match_scores  # Pass match_scores to avoid recomputing gaps
    )
    
    # Compile final report
    report = {
        "is_grad_student_job": job_skills_json.get("is_grad_student_job", False),
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

