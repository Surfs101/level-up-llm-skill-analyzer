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
    gaps_empty, _rank_missing_skills, recommend_courses_from_gaps
)
from recommend_projects import (
    get_resume_skills as get_resume_skills_projects,
    build_prompt as build_project_prompt, enforce_top_schema
)

# Load environment
load_dotenv()
BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]


def extract_skills_from_text(resume_text: str) -> dict:
    """
    Extract skills from resume text using OpenAI with rule-based augmentation.
    Includes domain expertise like Machine Learning, Deep Learning, Data Science, etc.
    """
    import re
    from typing import Set, List, Dict
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Rule-based vocabulary for domain expertise
    KNOWN_LANGUAGES = {
        "python","java","c","c++","c#","javascript","typescript","go","rust","ruby","php","sql","scala","kotlin","swift","r","matlab"
    }
    KNOWN_FRAMEWORKS = {
        "react","angular","vue","django","flask","spring","fastapi","pytorch","tensorflow","keras","scikit-learn","sklearn","pandas","numpy","opencv","spark","hadoop","airflow","dbt","next.js","node.js","express","laravel",".net","dotnet","rails","bootstrap","tailwind css","material ui"
    }
    DOMAIN_TERMS = {
        "machine learning", "deep learning", "artificial intelligence", "ai", "ml", "dl",
        "neural networks", "cnn", "rnn", "lstm", "transformer", "attention mechanism",
        "natural language processing", "nlp", "computer vision", "cv", "data science",
        "data analytics", "predictive modeling", "reinforcement learning", "rl",
        "supervised learning", "unsupervised learning", "transfer learning",
        "feature engineering", "model training", "model evaluation", "mlops",
        "data engineering", "big data", "data mining", "statistical analysis",
        "time series analysis", "recommendation systems", "anomaly detection",
        "clustering", "classification", "regression", "optimization", "gradient descent"
    }
    
    def find_terms_in_text(terms: List[str], text: str) -> Set[str]:
        """Find terms in text with word-boundary matching, return original-cased hits."""
        hits: Set[str] = set()
        for term in terms:
            if not term:
                continue
            # Build regex that avoids partial matches inside longer tokens
            pat = re.compile(rf"(?<![A-Za-z0-9+#.]){re.escape(term)}(?![A-Za-z0-9.+#-])", re.IGNORECASE)
            for m in pat.finditer(text):
                # Grab original slice to preserve case
                hits.add(text[m.start():m.end()])
                break
        return hits
    
    def rule_based_extract(text: str) -> Dict[str, List[str]]:
        """Extract skills using rule-based matching."""
        base_vocab = set().union(KNOWN_LANGUAGES, KNOWN_FRAMEWORKS, DOMAIN_TERMS, {
            "git","github","gitlab","docker","kubernetes","aws","gcp","azure","sagemaker","vertex ai","bigquery","databricks","mlflow","airbyte","snowflake","postgres","mysql","mongodb","redis","elasticsearch","tableau","power bi","looker","jira","confluence","jenkins","circleci","terraform","ansible"
        })
        hits = find_terms_in_text(sorted(base_vocab, key=len, reverse=True), text)
        
        def bucketize(term: str) -> str:
            t = term.lower()
            if t in KNOWN_LANGUAGES:
                return "ProgrammingLanguages"
            if t in DOMAIN_TERMS or t in KNOWN_FRAMEWORKS:
                return "FrameworksLibraries"
            return "ToolsPlatforms"
        
        buckets: Dict[str, Set[str]] = {"ProgrammingLanguages": set(), "FrameworksLibraries": set(), "ToolsPlatforms": set()}
        for h in hits:
            buckets[bucketize(h)].add(h)
        
        return {
            "ProgrammingLanguages": sorted(buckets["ProgrammingLanguages"]),
            "FrameworksLibraries": sorted(buckets["FrameworksLibraries"]),
            "ToolsPlatforms": sorted(buckets["ToolsPlatforms"]),
        }
    
    def merge_outputs(llm_obj: Dict[str, List[str]], rule_obj: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Merge LLM and rule-based outputs, preserving original casing."""
        out: Dict[str, List[str]] = {k: [] for k in ["ProgrammingLanguages","FrameworksLibraries","ToolsPlatforms"]}
        for b in out.keys():
            llm_list = llm_obj.get(b, []) if isinstance(llm_obj, dict) else []
            rule_list = rule_obj.get(b, []) if isinstance(rule_obj, dict) else []
            seen = set()
            merged: List[str] = []
            for src in [llm_list, rule_list]:
                for s in src:
                    key = s.strip().lower()
                    if key and key not in seen:
                        merged.append(s)
                        seen.add(key)
            out[b] = merged
        return out
    
    # LLM-based extraction with improved prompt
    prompt = f"""
You are an expert résumé parser.
Make sure to list only the languages and skills that are actually mentioned in the résumé.

Extract ALL technical skills from the resume text below, including:
- Programming languages (Python, Java, etc.)
- Frameworks and libraries (React, PyTorch, TensorFlow, etc.)
- Tools and platforms (Git, Docker, AWS, etc.)
- Domain expertise areas (Machine Learning, Deep Learning, Data Science, AI, Computer Vision, NLP, etc.)
- Methodologies and techniques (Supervised Learning, Neural Networks, Feature Engineering, etc.)

IMPORTANT: 
- Include domain expertise areas like "Machine Learning", "Deep Learning", "Data Science", "AI", "Computer Vision", "NLP" if they appear anywhere in the resume (including courses, projects, experience, education sections).
- Include methodologies and techniques mentioned in the resume.
- Classify domain expertise and methodologies into "FrameworksLibraries" bucket.

Classify skills into:
- ProgrammingLanguages: Specific programming languages
- FrameworksLibraries: Frameworks, libraries, domain expertise (ML, AI, Data Science), methodologies
- ToolsPlatforms: Tools, platforms, cloud services, databases

Output must be STRICT JSON only in this format:
{{
  "skills": {{
    "ProgrammingLanguages": ["Python", "SQL"],
    "FrameworksLibraries": ["React", "scikit-learn", "Machine Learning", "Deep Learning"],
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
    llm_data = json.loads(raw)
    
    # Rule-based extraction for recall boost
    rule_based = rule_based_extract(resume_text)
    
    # Merge LLM and rule-based results
    merged_skills = merge_outputs(llm_data.get("skills", {}), rule_based)
    
    return {"skills": merged_skills}


def extract_job_skills_from_text(job_description_text: str) -> dict:
    """Extract required/preferred skills from job description using OpenAI."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are an expert job-description parser.

Task:
1) Identify the MAIN DOMAIN/FIELD of this job (e.g., "Machine Learning", "AI", "Data Science", "MLOps", "Software Engineering", "DevOps", "Cloud Computing", "Cybersecurity", etc.). If the job is clearly in a technical domain, include this domain as a skill in FrameworksLibraries bucket (e.g., "Machine Learning", "Artificial Intelligence", "Data Science", "MLOps").

2) Extract ALL technical skills explicitly present in the text OR implied by the job domain.

3) Split them into two groups:
   - required  = cues like "required", "must", "we need", "minimum"
   - preferred = cues like "preferred", "nice to have", "plus", "bonus"

4) Classify each group into EXACTLY these buckets:
   - ProgrammingLanguages: specific programming languages (Python, Java, etc.)
   - FrameworksLibraries: frameworks, libraries, AND the main job domain/field if technical (e.g., "Machine Learning", "Data Science", "MLOps", "AI")
   - ToolsPlatforms: tools, platforms, cloud services

IMPORTANT: If the job title or description clearly indicates a technical domain (ML/AI, Data Science, MLOps, DevOps, etc.), you MUST include that domain name in the FrameworksLibraries bucket as a skill. Examples:
- "MLOps Engineer" → add "MLOps" to FrameworksLibraries
- "Data Scientist" → add "Data Science" to FrameworksLibraries  
- "Machine Learning Engineer" → add "Machine Learning" to FrameworksLibraries
- "AI Engineer" → add "Artificial Intelligence" or "AI" to FrameworksLibraries

5) Determine if this job requires a graduate degree (Master's or PhD). Look for cues like:
   - "Master's degree required", "PhD required", "graduate degree"
   - "Master's or PhD", "MS/PhD", "graduate student"
   - Job titles like "Research Intern", "PhD Intern", "Graduate Intern"
   - If the job explicitly requires Master's or PhD, set "is_grad_student_job" to true, otherwise false.

Return STRICT JSON ONLY in this format (no extra text):

{{
  "is_grad_student_job": false,
  "required": {{
    "skills": {{
      "ProgrammingLanguages": ["Python", "SQL"],
      "FrameworksLibraries": ["React", "scikit-learn", "Machine Learning"],
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
    
    # Preserve is_grad_student_job flag if present
    is_grad_student_job = data.get("is_grad_student_job", False)
    
    # Ensure schema
    out = {"required": {}, "preferred": {}, "is_grad_student_job": is_grad_student_job}
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
    """Get course recommendations based on skill gaps using MongoDB."""
    # Use the new MongoDB-based recommendation function
    recommendations = recommend_courses_from_gaps(
        resume_json=resume_json,
        job_json=job_json,
        role=role,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1
    )
    
    # The function returns a dict with 'free_courses' and 'paid_courses' lists
    # Format it to match the expected structure
    return recommendations


def get_project_recommendations(job_description_text: str, resume_json: dict, job_json: dict, primary_gap_skill: str | None = None, course_recommendations: dict | None = None) -> dict:
    """Get project recommendations based on job, resume, explicit gaps, and course recommendations.
    
    Args:
        job_description_text: Raw job description text
        resume_json: Resume skills JSON
        job_json: Job skills JSON (required/preferred)
        primary_gap_skill: Primary missing skill to focus on (same as course recommendations)
        course_recommendations: Course recommendations dict (from get_course_recommendations) to align projects with
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
    
    prompt = build_project_prompt(job_description_text, resume_skills, gaps, primary_gap_skill=primary_gap_skill, course_recommendations=course_recommendations)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
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
    
    # Step 3: Score skills match
    step_msg = "Computing skills match scores..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    w_req, w_pref = parse_weights(weights)
    match_scores = score_match(resume_skills_json, job_skills_json, w_req, w_pref)
    
    # Step 4: Get course recommendations (and compute primary gap skill)
    step_msg = "Generating course recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
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
    
    # Step 5: Get project recommendations (sync with course recommendations via primary gap skill and course data)
    step_msg = "Generating project recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    project_recommendations = get_project_recommendations(
        job_description_text,
        resume_skills_json,
        job_skills_json,
        primary_gap_skill=primary_gap_skill,
        course_recommendations=course_recommendations  # Pass course recommendations to align projects
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

