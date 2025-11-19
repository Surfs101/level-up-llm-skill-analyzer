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
from recommend_courses import (
    get_resume_skills,
    get_job_required_skills,
    get_job_preferred_skills,
    compute_gaps,
    gaps_empty,
    _rank_missing_skills,
    recommend_courses_from_gaps,
    recommend_courses_for_job_skills,
    TARGET_BUCKETS,
)
from recommend_projects import (
    get_resume_skills as get_resume_skills_projects,
    build_prompt as build_project_prompt, enforce_top_schema
)

# Load environment
load_dotenv()
BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]

CANONICAL_SKILL_MAP = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "machine-learning": "Machine Learning",
    "machine learing": "Machine Learning",
    "m.l.": "Machine Learning",
    "r": "R",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "artificial-intelligence": "Artificial Intelligence",
    "software engineering": "Software Engineering",
    "software engineer": "Software Engineering",
    "software-engineering": "Software Engineering",
    "software developer": "Software Engineering",
    "software development": "Software Engineering",
    "software-development": "Software Engineering",
    "swe": "Software Engineering",
    "data science": "Data Science",
    "data scientist": "Data Science",
    "data-science": "Data Science",
    "data analytics": "Data Analytics",
    "data analyst": "Data Analytics",
    "data-analytics": "Data Analytics",
    "mlops": "MLOps",
    "m.l.ops": "MLOps",
}

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
}


def canonicalize_skill_name(skill: str) -> str:
    if not skill:
        return ""
    normalized = str(skill).strip()
    key = normalized.lower()
    return CANONICAL_SKILL_MAP.get(key, normalized)


def canonicalize_skills_by_bucket(skills_dict: dict) -> dict:
    if not isinstance(skills_dict, dict):
        return {bucket: [] for bucket in BUCKETS}
    
    buckets = set(BUCKETS) | set(skills_dict.keys())
    canonicalized = {}
    
    for bucket in buckets:
        seen = set()
        canonicalized[bucket] = []
        for skill in skills_dict.get(bucket, []) or []:
            canonical = canonicalize_skill_name(skill)
            key = canonical.lower()
            if key and key not in seen:
                canonicalized[bucket].append(canonical)
                seen.add(key)
    
    return canonicalized


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
    Post-process extracted skills to ensure single-letter languages like "R" and "C" 
    are included if they appear in the job description text.
    This is a safety net in case the LLM misses them.
    """
    SINGLE_LETTER_LANGS = {"r": "R", "c": "C"}
    
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
                    required_skills["ProgrammingLanguages"].append(lang_upper)


def ensure_critical_domains_in_skills(text: str, skills_dict: dict):
    if not text or not isinstance(skills_dict, dict):
        return
    
    target_bucket = "FrameworksLibraries"
    skills_dict.setdefault(target_bucket, [])
    bucket_list = skills_dict[target_bucket]
    
    for canonical, patterns in CRITICAL_DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                bucket_list.append(canonical)
                break


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
        "clustering", "classification", "regression", "optimization", "gradient descent",
        "software engineering", "software engineer", "software development", "software developer"
    }
    
    SINGLE_LETTER_LANGS = {"r"}

    def find_terms_in_text(terms: List[str], text: str) -> Set[str]:
        """Find terms in text with word-boundary matching, return original-cased hits."""
        hits: Set[str] = set()
        for term in terms:
            if not term:
                continue
            # Build regex that avoids partial matches inside longer tokens
            if len(term) == 1 and term in SINGLE_LETTER_LANGS:
                pattern = rf"(?<![A-Za-z0-9&#/]){re.escape(term.upper())}(?![A-Za-z0-9&#/])"
                pat = re.compile(pattern)
            else:
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
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw = response.choices[0].message.content
    llm_data = json.loads(raw)
    
    # Rule-based extraction for recall boost
    rule_based = rule_based_extract(resume_text)
    
    # Merge LLM and rule-based results
    merged_skills = merge_outputs(llm_data.get("skills", {}), rule_based)
    ensure_critical_domains_in_skills(resume_text, merged_skills)
    merged_skills = canonicalize_skills_by_bucket(merged_skills)
    
    return {"skills": merged_skills}


def extract_job_skills_from_text(job_description_text: str) -> dict:
    """Extract required/preferred skills from job description using OpenAI."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are an expert job-description parser.

Task:
1) Identify the MAIN DOMAIN/FIELD of this job (e.g., "Machine Learning", "AI", "Data Science", "MLOps", "Software Engineering", "DevOps", "Cloud Computing", "Cybersecurity", etc.). If the job is clearly in a technical domain, include this domain as a skill in FrameworksLibraries bucket (e.g., "Machine Learning", "Artificial Intelligence", "Data Science", "MLOps").

2) Extract ONLY technical skills that can be learned through courses or projects. Focus on:
   - Specific programming languages (Python, Java, Go, JavaScript, R, C, C++, etc.) - CRITICAL: Include single-letter languages like "R" and "C" even when they appear in comma-separated lists (e.g., "Python, R, SQL" must extract "R" as a skill)
   - Specific frameworks and libraries (React, Angular, Vue, TensorFlow, PyTorch, etc.)
   - Specific tools, platforms, and services (Docker, Kubernetes, AWS, GCP, Azure, MongoDB, PostgreSQL, Redis, etc.)
   - Technical domains that can be learned (Machine Learning, Data Science, AI, MLOps, etc.)

3) DO NOT extract:
   - Practices or methodologies (CI/CD, automated testing, monitoring, observability, alerting, drift detection, version control)
   - Concepts or techniques (RAG, Retrieval-Augmented Generation, Agentic AI, Model Context Protocol, MCP)
   - Generic terms that are too broad or abstract
   - Soft skills or non-technical requirements
   
   Only extract concrete, learnable technical skills that can be taught in courses or practiced in projects.

4) Split them into two groups:
   - required  = cues like "required", "must", "we need", "minimum"
   - preferred = cues like "preferred", "nice to have", "plus", "bonus"
   
CRITICAL: A skill should appear in ONLY ONE section. If a skill is marked as "required", it MUST NOT appear in "preferred". If a skill appears in both sections, prioritize it as "required" and remove it from "preferred".

5) Classify each group into EXACTLY these buckets:
   - ProgrammingLanguages: specific programming languages (Python, Java, etc.)
   - FrameworksLibraries: frameworks, libraries, AND the main job domain/field if technical (e.g., "Machine Learning", "Data Science", "MLOps", "AI")
   - ToolsPlatforms: tools, platforms, cloud services

IMPORTANT: If the job title or description clearly indicates a technical domain (ML/AI, Data Science, MLOps, DevOps, etc.), you MUST include that domain name in the FrameworksLibraries bucket as a skill. Examples:
- "MLOps Engineer" → add "MLOps" to FrameworksLibraries
- "Data Scientist" → add "Data Science" to FrameworksLibraries  
- "Machine Learning Engineer" → add "Machine Learning" to FrameworksLibraries
- "AI Engineer" → add "Artificial Intelligence" or "AI" to FrameworksLibraries

6) Determine if this job requires a graduate degree (Master's or PhD). Look for cues like:
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
        model="gpt-5.1",
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
    
    # Ensure critical domains are captured consistently
    # Only add to required first, then preferred if not already in required
    ensure_critical_domains_in_skills(job_description_text, out["required"]["skills"])
    
    # Canonicalize both sections
    out["required"]["skills"] = canonicalize_skills_by_bucket(out["required"]["skills"])
    out["preferred"]["skills"] = canonicalize_skills_by_bucket(out["preferred"]["skills"])
    
    # Filter out non-recommendable skills (practices, methodologies, concepts)
    out["required"]["skills"] = filter_non_recommendable_skills(out["required"]["skills"])
    out["preferred"]["skills"] = filter_non_recommendable_skills(out["preferred"]["skills"])
    
    # Post-process: Ensure single-letter languages like "R" and "C" are extracted if they appear in the text
    ensure_single_letter_languages(job_description_text, out["required"]["skills"], out["preferred"]["skills"])
    
    # CRITICAL: Remove any skills from preferred that are already in required
    # This ensures no duplication between required and preferred
    required_flat = set()
    for bucket in BUCKETS:
        required_skills_list = out["required"]["skills"].get(bucket, [])
        # Normalize to lowercase for comparison
        required_flat.update({s.lower().strip() for s in required_skills_list if s})
    
    # Remove duplicates from preferred
    for bucket in BUCKETS:
        preferred_skills_list = out["preferred"]["skills"].get(bucket, [])
        # Filter out any skills that are already in required (case-insensitive)
        filtered_preferred = [
            s for s in preferred_skills_list 
            if s and s.lower().strip() not in required_flat
        ]
        out["preferred"]["skills"][bucket] = filtered_preferred
    
    # Now add critical domains to preferred only if they're not already in required
    # (This is a fallback if the LLM didn't extract them)
    ensure_critical_domains_in_skills(job_description_text, out["preferred"]["skills"])
    
    # Final deduplication pass after adding critical domains
    required_flat = set()
    for bucket in BUCKETS:
        required_skills_list = out["required"]["skills"].get(bucket, [])
        required_flat.update({s.lower().strip() for s in required_skills_list if s})
    
    for bucket in BUCKETS:
        preferred_skills_list = out["preferred"]["skills"].get(bucket, [])
        filtered_preferred = [
            s for s in preferred_skills_list 
            if s and s.lower().strip() not in required_flat
        ]
        out["preferred"]["skills"][bucket] = filtered_preferred
    
    return out


def get_course_recommendations(resume_json: dict, job_json: dict, role: str = "Target Role") -> dict:
    """
    Get course recommendations with the following priority:

    1) **Missing-skill-based** (primary): recommend courses to close concrete gaps.
    2) **Job-based fallback**: if there are no courses for the missing skills
       (e.g., no "Tableau" course), recommend courses based on the job's core
       skills/domain (e.g., "Data Analysis", "Machine Learning").
    3) If neither path finds anything, return empty course lists.
    
    Additionally, if one paid course doesn't cover all skills, fetch a second
    paid course targeting the second most important missing skill.
    """
    # Compute gaps to identify top critical skills
    have = get_resume_skills(resume_json)
    need_required = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need_required)
    
    # If no REQUIRED gaps, fall back to PREFERRED gaps
    if gaps_empty(gaps):
        need_pref = get_job_preferred_skills(job_json)
        gaps = compute_gaps(have, need_pref)
    
    # Rank missing skills by importance
    ranked_skills = _rank_missing_skills(gaps)
    top_critical_skills = ranked_skills[:2] if len(ranked_skills) >= 2 else ranked_skills
    
    # First: try based on missing skills (gaps) - get 1 paid course initially
    recommendations = recommend_courses_from_gaps(
        resume_json=resume_json,
        job_json=job_json,
        role=role,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1,
    )

    free_courses = recommendations.get("free_courses") or []
    paid_courses = recommendations.get("paid_courses") or []
    uncovered_skills = recommendations.get("uncovered_skills", [])

    # Check if we need a second paid course
    # If there are uncovered skills and we have at least 2 critical skills, fetch a second course
    if uncovered_skills and len(top_critical_skills) >= 2 and len(paid_courses) == 1:
        # Get skills covered by the first paid course
        first_course_skills = set(paid_courses[0].get("skills_covered", []))
        
        # Specifically target the SECOND most important skill (index 1) for the second course
        # This ensures we get one course for each of the top 2 critical skills
        second_target_skill = None
        if len(top_critical_skills) >= 2:
            # Target the second critical skill (index 1)
            second_critical_skill = top_critical_skills[1]
            # Only use it if it's not already covered by the first course
            if second_critical_skill not in first_course_skills:
                second_target_skill = second_critical_skill
            else:
                # If the second skill is already covered, find the next uncovered critical skill
                for skill in top_critical_skills[2:]:  # Check skills beyond the top 2
                    if skill not in first_course_skills:
                        second_target_skill = skill
                        break
        
        # If we found a second critical skill to target, fetch a course for it
        if second_target_skill:
            print(f"Debug: First paid course doesn't cover all skills. Fetching second course for: {second_target_skill}")
            
            # Fetch courses specifically targeting the second skill using job-based fallback
            # Create a temporary job JSON that only requires the second skill
            # Determine which bucket the second skill belongs to
            skill_bucket = None
            for bucket in ["ToolsPlatforms", "FrameworksLibraries", "ProgrammingLanguages"]:
                if bucket in gaps and second_target_skill in gaps.get(bucket, []):
                    skill_bucket = bucket
                    break
            
            # If we couldn't determine the bucket, default to ToolsPlatforms
            if not skill_bucket:
                skill_bucket = "ToolsPlatforms"
            
            temp_job_json = {
                "required": {
                    "skills": {
                        "ToolsPlatforms": [],
                        "FrameworksLibraries": [],
                        "ProgrammingLanguages": [],
                    }
                },
                "preferred": {"skills": {}}
            }
            temp_job_json["required"]["skills"][skill_bucket] = [second_target_skill]
            
            # Fetch a second paid course targeting this specific skill
            # OPTIMIZATION: Reduced from 10 to 3 to avoid excessive processing
            second_recommendations = recommend_courses_from_gaps(
                resume_json=resume_json,
                job_json=temp_job_json,
                role=role,
                require_free=False,
                require_paid=True,  # Only paid courses
                max_free=0,
                max_paid=3,  # Reduced from 10 to 3 for faster processing
            )
            
            second_paid_courses = second_recommendations.get("paid_courses", [])
            
            # Find a course that covers the second target skill and is different from the first
            first_course_title = paid_courses[0].get("title", "").lower()
            found_second = False
            
            for second_course in second_paid_courses:
                second_course_title = second_course.get("title", "").lower()
                second_course_skills = set(second_course.get("skills_covered", []))
                
                # Check if this course covers the target skill and is different from the first
                if (second_target_skill in second_course_skills and 
                    second_course_title != first_course_title):
                    paid_courses.append(second_course)
                    print(f"Debug: Added second paid course targeting '{second_target_skill}': {second_course.get('title', 'N/A')}")
                    found_second = True
                    break
            
            # If we didn't find a perfect match, take the best available second course (different from first)
            if not found_second and second_paid_courses:
                for second_course in second_paid_courses:
                    second_course_title = second_course.get("title", "").lower()
                    if second_course_title != first_course_title:
                        paid_courses.append(second_course)
                        print(f"Debug: Added second paid course (best available): {second_course.get('title', 'N/A')}")
                        found_second = True
                        break
            
            # Update recommendations with the second course
            paid_courses = paid_courses[:2]  # Limit to 2 and update local variable
            recommendations["paid_courses"] = paid_courses  # Update recommendations
            print(f"Debug: Final paid courses count: {len(paid_courses)}")
            
            # Recompute coverage with both courses
            all_covered_skills = set()
            for course in paid_courses + free_courses:
                all_covered_skills.update(course.get("skills_covered", []))
            
            # Recompute uncovered skills
            target_skills_set = set(ranked_skills)
            new_uncovered = sorted(list(target_skills_set - all_covered_skills))
            recommendations["uncovered_skills"] = new_uncovered
            
            # Recompute skill coverage map
            skill_coverage = defaultdict(list)
            for course in paid_courses + free_courses:
                title = course.get("title", "")
                for skill in course.get("skills_covered", []):
                    if skill in target_skills_set:
                        if title and title not in skill_coverage[skill]:
                            skill_coverage[skill].append(title)
            recommendations["skill_coverage"] = dict(skill_coverage)
            recommendations["coverage_percentage"] = round(
                100 * (len(target_skills_set) - len(new_uncovered)) / max(1, len(target_skills_set))
            )

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


def get_project_recommendations(job_description_text: str, resume_json: dict, job_json: dict, primary_gap_skill: str | None = None, course_recommendations: dict | None = None) -> dict:
    """Get project recommendations based on job, resume, explicit gaps, and course recommendations.
    
    CRITICAL: Projects MUST sync with course recommendations - use the EXACT same missing skills
    that courses are targeting, not independently computed gaps.
    
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
    
    # CRITICAL SYNC: Use the EXACT same missing skills that courses are targeting
    # Extract target skills from course recommendations (skills courses are covering)
    target_missing_skills = set()
    if course_recommendations:
        # Get all skills covered by courses (these are the target missing skills)
        paid_courses = course_recommendations.get("paid_courses", [])
        free_courses = course_recommendations.get("free_courses", [])
        for course in paid_courses + free_courses:
            skills_covered = course.get("skills_covered", [])
            target_missing_skills.update(skills_covered)
        
        # Also include uncovered skills (skills courses couldn't find but are still missing)
        uncovered_skills = course_recommendations.get("uncovered_skills", [])
        target_missing_skills.update(uncovered_skills)
    
    # If we have target skills from courses, use those to build gaps dict
    # Otherwise, fall back to computing gaps from job JSON (for backward compatibility)
    if target_missing_skills:
        # Build gaps dict based on course target skills
        # This ensures projects use the EXACT same skills courses are targeting
        gaps = {bucket: [] for bucket in TARGET_BUCKETS}
        have_flat = {s for bucket in have.values() for s in bucket}
        
        # Categorize target missing skills into buckets
        for skill in target_missing_skills:
            # Check which bucket this skill belongs to in the original job requirements
            need_required = get_job_required_skills(job_json)
            need_preferred = get_job_preferred_skills(job_json)
            
            # Find the bucket for this skill
            skill_bucket = None
            for bucket in TARGET_BUCKETS:
                if skill in need_required.get(bucket, []) or skill in need_preferred.get(bucket, []):
                    skill_bucket = bucket
                    break
            
            # If we couldn't find it, try to infer from the skill name
            if not skill_bucket:
                skill_lower = skill.lower()
                if any(prog in skill_lower for prog in ["python", "java", "javascript", "sql", "r", "c++", "go", "rust"]):
                    skill_bucket = "ProgrammingLanguages"
                elif any(tool in skill_lower for tool in ["docker", "kubernetes", "aws", "gcp", "azure", "tableau", "powerbi", "bigquery", "looker"]):
                    skill_bucket = "ToolsPlatforms"
                else:
                    skill_bucket = "FrameworksLibraries"  # Default
            
            # Only add if it's actually missing (not in resume)
            if skill not in have_flat:
                gaps[skill_bucket].append(skill)
        
        # Sort each bucket
        for bucket in TARGET_BUCKETS:
            gaps[bucket] = sorted(gaps[bucket])
        
        print(f"Debug: Using course-synced gaps: {sum(len(v) for v in gaps.values())} missing skills from course recommendations")
    else:
        # Fallback: compute gaps independently (shouldn't happen if courses were found)
        need = get_job_required_skills(job_json)
        gaps = compute_gaps(have, need)
        
        # If no required gaps, try preferred
        if gaps_empty(gaps):
            need = get_job_preferred_skills(job_json)
            gaps = compute_gaps(have, need)
        print(f"Debug: Using independently computed gaps (no course sync): {sum(len(v) for v in gaps.values())} missing skills")
    
    prompt = build_project_prompt(job_description_text, resume_skills, gaps, primary_gap_skill=primary_gap_skill, course_recommendations=course_recommendations)
    
    response = client.chat.completions.create(
        model="gpt-5.1",
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

