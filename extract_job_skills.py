# extract_job_skills.py
import os
import sys
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]

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

def ensure_schema(d):
    """Ensure required/preferred blocks exist and contain all buckets."""
    out = {"required": {}, "preferred": {}}
    for side in ["required", "preferred"]:
        block = d.get(side, {}) or {}
        # allow either flat dict of buckets or nested {"skills": {...}}
        skills = block.get("skills", block)
        clean = {}
        for b in BUCKETS:
            v = skills.get(b, [])
            clean[b] = v if isinstance(v, list) else []
        out[side] = {"skills": clean}
    return out

def main():
    # --- Step 1: Load API key ---
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # --- Step 2: CLI args ---
    if len(sys.argv) < 2:
        print("❌ Please provide a job description .txt file as an argument.")
        print("Example: python extract_job_skills.py job_description.txt")
        sys.exit(1)
    file_name = sys.argv[1]

    # --- Step 3: Read the input file ---
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            jd_text = f.read()
    except FileNotFoundError:
        print(f"❌ File '{file_name}' not found.")
        sys.exit(1)

    # --- Step 4: Prompt (same buckets & shape as resume extractor) ---
    prompt = f"""
You are an expert job-description parser.

Task:
1) Identify the MAIN DOMAIN/FIELD of this job (e.g., "Machine Learning", "AI", "Data Science", "MLOps", "Software Engineering", "DevOps", "Cloud Computing", "Cybersecurity", etc.). If the job is clearly in a technical domain, include this domain as a skill in FrameworksLibraries bucket (e.g., "Machine Learning", "Artificial Intelligence", "Data Science", "MLOps").

2) Extract ONLY technical skills that can be learned through courses or projects. Focus on:
   - Specific programming languages (Python, Java, Go, JavaScript, R, C, C++, etc.) - IMPORTANT: Include single-letter languages like "R" and "C" even when they appear in comma-separated lists (e.g., "Python, R, SQL" should extract "R" as a skill)
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
{jd_text}
""".strip()

    # --- Step 5: Call GPT (same model + response_format as resume extractor) ---
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}  # same enforcement as your resume script
    )

    # --- Step 6: Parse + normalize + save JSON ---
    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
        # Preserve is_grad_student_job flag if present
        is_grad_student_job = data.get("is_grad_student_job", False)
        data = ensure_schema(data)
        data["is_grad_student_job"] = is_grad_student_job
        
        # Filter out non-recommendable skills (practices, methodologies, concepts)
        def filter_non_recommendable_skills(skills_dict):
            """Remove skills that cannot be recommended."""
            if not isinstance(skills_dict, dict):
                return skills_dict
            
            non_recommendable = {
                "ci/cd", "cicd", "ci/cd pipelines", "continuous integration", "continuous deployment",
                "automated testing", "testing", "monitoring", "observability", "alerting",
                "drift detection", "version control", "agile", "scrum",
                "rag", "retrieval-augmented generation", "agentic ai", "mcp", "model context protocol",
                "prompt engineering", "fine-tuning", "transfer learning",
                "best practices", "software development", "problem solving", "troubleshooting",
                "code review", "documentation", "api design", "system design"
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
                    if skill_lower not in non_recommendable:
                        is_non_rec = False
                        for non_rec in non_recommendable:
                            if non_rec in skill_lower or skill_lower in non_rec:
                                is_non_rec = True
                                break
                        if not is_non_rec:
                            filtered_skills.append(skill)
                filtered[bucket] = filtered_skills
            return filtered
        
        # Apply filter to both required and preferred
        required_skills = filter_non_recommendable_skills(data.get("required", {}).get("skills", {}))
        preferred_skills = filter_non_recommendable_skills(data.get("preferred", {}).get("skills", {}))
        data["required"]["skills"] = required_skills
        data["preferred"]["skills"] = preferred_skills
        
        # Post-process: Ensure single-letter languages like "R" and "C" are extracted if they appear in the text
        ensure_single_letter_languages(jd_text, required_skills, preferred_skills)
        data["required"]["skills"] = required_skills
        data["preferred"]["skills"] = preferred_skills
        
        # CRITICAL: Remove any skills from preferred that are already in required
        # This ensures no duplication between required and preferred
        
        # Build flat set of required skills (case-insensitive)
        required_flat = set()
        for bucket in BUCKETS:
            required_list = required_skills.get(bucket, [])
            required_flat.update({str(s).lower().strip() for s in required_list if s})
        
        # Remove duplicates from preferred
        for bucket in BUCKETS:
            preferred_list = preferred_skills.get(bucket, [])
            filtered_preferred = [
                s for s in preferred_list 
                if s and str(s).lower().strip() not in required_flat
            ]
            preferred_skills[bucket] = filtered_preferred
        
        data["preferred"]["skills"] = preferred_skills
        
        output_file = os.path.splitext(file_name)[0] + "_skills.json"
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2, ensure_ascii=False)
        
        # Output JSON ONLY to stdout (for programmatic use)
        # Send informative messages to stderr instead so they don't interfere with JSON parsing
        json_output = json.dumps(data, indent=2, ensure_ascii=False)
        print(json_output, file=sys.stdout)
        print(f"✅ Skills data saved to: {output_file}", file=sys.stderr)
    except json.JSONDecodeError:
        print("⚠️ JSON decoding failed, raw response:", file=sys.stderr)
        print(raw, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
