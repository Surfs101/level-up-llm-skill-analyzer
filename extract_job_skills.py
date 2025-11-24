# extract_job_skills.py
import os
import sys
import json
import re
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI

# Import shared normalization
from skill_normalization import (
    BUCKETS,
    canonicalize_skills_by_bucket,
    canonicalize_skill_name,
)

# Load environment variables
load_dotenv()

# Cues that the JD explicitly distinguishes preferred / nice-to-have skills
PREFERRED_CUES_PATTERN = re.compile(
    r"\b(preferred|nice to have|nice-to-have|good to have|bonus|"
    r"would be a plus|a plus|plus)\b",
    flags=re.IGNORECASE,
)

def has_preferred_cues(text: str) -> bool:
    """Return True if the job description explicitly mentions preferred / nice-to-have cues."""
    return bool(PREFERRED_CUES_PATTERN.search(text or ""))


def ensure_schema(d):
    """Ensure required/preferred blocks exist and contain all buckets (3 buckets only)."""
    out = {"required": {}, "preferred": {}}
    for side in ["required", "preferred"]:
        block = d.get(side, {}) or {}
        skills = block.get("skills", block)
        clean = {}
        for b in BUCKETS:
            v = skills.get(b, [])
            clean[b] = v if isinstance(v, list) else []
        out[side] = {"skills": clean}
    return out


def extract_job_skills_from_text(job_description_text: str) -> dict:
    """
    Extract required/preferred skills from job description using OpenAI.
    This is the main reusable function that can be imported by other modules.
    
    The LLM is the single source of truth for:
    - Which skills are required vs preferred
    - How skills are bucketed (ProgrammingLanguages, FrameworksLibraries, ToolsPlatforms)
    
    Args:
        job_description_text: Raw text content from job description
    
    Returns:
        Dictionary with structure: {"required": {"skills": {...}}, "preferred": {"skills": {...}}, "is_grad_student_job": bool}
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # LLM-based extraction prompt - LLM decides required vs preferred classification
    prompt = f"""
You are an expert job-description parser.

Extract ONLY learnable technical skills from the job description below. Learnable skills are technologies, tools, languages, frameworks, libraries, and fields that can be taught through courses, tutorials, or documentation.

ONLY EXTRACT:
- Programming languages (Python, Java, C, C++, JavaScript, Go, Rust, etc.) - IMPORTANT: Only extract "R" or "C" if they actually appear in the job description text as programming languages. Do NOT infer or guess "R" if it is not explicitly mentioned.
- Frameworks and libraries (React, Angular, Vue, PyTorch, TensorFlow, scikit-learn, etc.)
- Tools and platforms (Git, Docker, Kubernetes, AWS, Azure, GCP, etc.)
- Databases (PostgreSQL, MongoDB, MySQL, NoSQL databases, etc.)
- Domain expertise fields (Machine Learning, Deep Learning, Data Science, AI, Agentic AI, RAG, Retrieval-Augmented Generation, Computer Vision, NLP, etc.)
- Specific technologies and libraries (OpenAI API, LangChain, etc.)

CRITICAL - DO NOT EXTRACT:
1. Generic terms or role descriptions:
   - "Full-stack development", "Full Stack", "Java Full Stack", "Full Stack Developer"
   - "Web Development", "Software Development", "Application Development" (unless it's a specific framework)
   - "Backend Development", "Frontend Development" (unless it's a specific technology)
   - Generic role descriptions or job titles

2. Processes, methodologies, or operational concepts (NOT learnable skills):
   - ML pipeline automation
   - Model versioning
   - Production deployment
   - Autonomous reasoning
   - Multi-step task execution
   - External tool integration
   - API integration (the concept, but DO extract specific APIs like "OpenAI API")
   - Document pipelines
   - Monitoring
   - Observability
   - Drift detection
   - Alerting
   - Automated testing (the concept, but DO extract specific testing tools like "Jest", "pytest")
   - CI/CD (the concept, but DO extract specific tools like "Jenkins", "GitHub Actions", "CircleCI")
   - Any skill that describes a process, workflow, or operational practice rather than a specific technology

3. Focus ONLY on concrete, specific technologies, languages, frameworks, tools, libraries, and learnable fields that can be taught.

4. Normalize skill variations to standard names:
   - "CSS3", "CSS 3", "CSS-3" → "CSS"
   - "HTML5", "HTML 5", "HTML-5" → "HTML"
   - "JavaScript", "JS", "ECMAScript" → "JavaScript"
   - "Node.js", "NodeJS", "Node" → "Node.js"
   - "AI", "Artificial Intelligence" → "Artificial Intelligence"
   - "ML", "Machine Learning" → "Machine Learning"
   - "LLM", "Large Language Models", "Large Language Model" → "Large Language Models"
   - "NLP", "Natural Language Processing" → "Natural Language Processing"
   - "CV", "Computer Vision" → "Computer Vision"
   - "RAG", "Retrieval-Augmented Generation" → "Retrieval-Augmented Generation"
   - "Agentic AI", "AI Agency" → "Agentic AI"
   - "Data Science", "Data Scientist" → "Data Science"
   - Apply this normalization consistently

5. Include domain expertise fields like "Machine Learning", "Deep Learning", "Data Science", "AI", "Agentic AI", "RAG", "Retrieval-Augmented Generation", "Computer Vision", "NLP" if they appear anywhere in the job description - these are learnable fields.
6. Classify domain expertise fields into "FrameworksLibraries" bucket.
7. DO NOT extract methodologies, processes, or operational practices - only extract concrete technologies and learnable fields.

Classify skills into:
- ProgrammingLanguages: Specific programming languages
- FrameworksLibraries: Frameworks, libraries, and domain expertise fields
  (Machine Learning, Deep Learning, Artificial Intelligence, Large Language Models, NLP, Computer Vision, Data Science, MLOps, LLMOps, RAG, Agentic AI, etc.)
- ToolsPlatforms: Tools, platforms, cloud providers, databases, analytics tools, DevOps tools, etc.

REQUIRED SKILLS (must-have for being seriously considered):
- Core technologies or tools used in day-to-day work for this job
- Stack mentioned in the job title or main responsibilities
- Skills explicitly marked as "required", "must", "we need", "minimum", "essential", "critical"
- If you are unsure, but the skill appears to be part of the core tech stack, treat it as required

PREFERRED SKILLS (nice-to-have / bonus):
- Skills explicitly marked as "preferred", "nice to have", "bonus", "plus", "would be a plus", "good to have"
- Secondary tools or technologies that are helpful but not critical
- Skills that would make a candidate stand out but aren't necessary

CRITICAL CLASSIFICATION RULES:
- A skill must appear in only one of required or preferred, not both.
- If a skill is marked as "required", it MUST NOT appear in "preferred".
- If the job description does NOT explicitly distinguish preferred/nice-to-have skills
  using words like "preferred", "nice to have", "nice-to-have", "good to have",
  "bonus", "plus", or "would be a plus", then you MUST put ALL extracted skills
  into "required" and leave ALL "preferred" buckets empty.
- Respect the JSON schema with required.skills and preferred.skills, each broken down into the three buckets: ProgrammingLanguages, FrameworksLibraries, ToolsPlatforms.

CRITICAL: Determine if this job requires a graduate degree (Master's or PhD).

Set "is_grad_student_job" to TRUE if you see ANY of these indicators:
- Degree requirements: "Master's degree required", "PhD required", "graduate degree required", "MS required", "Master's or PhD", "MS/PhD", "Masters or PhD"
- Education qualifications: "currently pursuing Master's", "pursuing PhD", "graduate student", "enrolled in graduate program", "current graduate student"
- Job titles: "Research Intern", "PhD Intern", "Graduate Intern", "Graduate Research Assistant", "PhD Student Intern", "Master's Student Intern"
- Academic focus: "Research position", "academic research", "thesis research", "graduate-level research"
- Enrollment status: "must be currently enrolled in graduate program", "graduate student status", "active graduate enrollment"
- Degree preference with strong language: "Master's preferred (required)", "PhD preferred (required)", "advanced degree required"

Set "is_grad_student_job" to FALSE if:
- Job only mentions "Bachelor's degree" without any mention of Master's/PhD
- Job says "Master's preferred" or "PhD preferred" WITHOUT saying "required"
- No education requirements are mentioned at all
- Job only requires "undergraduate degree" or "Bachelor's degree"

IMPORTANT: Be thorough in checking the entire job description for graduate degree requirements. Set to true if there's ANY indication that Master's or PhD is required.

Output must be STRICT JSON only in this format:
{{
  "is_grad_student_job": false,
  "required": {{
    "skills": {{
      "ProgrammingLanguages": ["Python", "SQL"],
      "FrameworksLibraries": ["React", "scikit-learn", "Machine Learning"],
      "ToolsPlatforms": ["Git", "Docker"]
    }}
  }},
  "preferred": {{
    "skills": {{
      "ProgrammingLanguages": ["Java"],
      "FrameworksLibraries": ["TensorFlow"],
      "ToolsPlatforms": ["Kubernetes"]
    }}
  }}
}}

Job Description:
{job_description_text}
"""
    
    # Call GPT-5.1 with temperature=0.0 for deterministic, consistent classification
    try:
        response = client.chat.completions.create(
            model="gpt-5.1",  # More capable model for accurate required/preferred classification
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0  # Deterministic output for consistency
        )
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            raise Exception(f"OpenAI API quota exceeded. Please check your billing and plan. Error: {error_msg}")
        else:
            raise Exception(f"Error calling OpenAI API for job skill extraction: {error_msg}")
    
    # Handle response
    raw = response.choices[0].message.content
    try:
        llm_data = json.loads(raw)
        
        # Extract data from LLM response (LLM is the single source of truth)
        required_skills = llm_data.get("required", {}).get("skills", {}) or {}
        preferred_skills = llm_data.get("preferred", {}).get("skills", {}) or {}
        is_grad_student_job = llm_data.get("is_grad_student_job", False)
        
        # Canonicalize both required and preferred skills
        required_skills = canonicalize_skills_by_bucket(required_skills)
        preferred_skills = canonicalize_skills_by_bucket(preferred_skills)
        
        # Build output structure
        data = {
            "required": {"skills": required_skills},
            "preferred": {"skills": preferred_skills},
            "is_grad_student_job": is_grad_student_job
        }
        
        # Ensure schema exists (all buckets present)
        data = ensure_schema(data)
        data["is_grad_student_job"] = is_grad_student_job

        # If the JD never explicitly mentions preferred / nice-to-have cues,
        # treat ALL extracted skills as required and clear preferred.
        if not has_preferred_cues(job_description_text):
            for bucket in BUCKETS:
                req_list = data["required"]["skills"].get(bucket, []) or []
                pref_list = data["preferred"]["skills"].get(bucket, []) or []

                # Merge preferred into required, avoiding duplicates (case-insensitive)
                existing = {str(s).lower().strip() for s in req_list if s}
                merged = req_list[:]

                for s in pref_list:
                    if s and str(s).lower().strip() not in existing:
                        merged.append(s)
                        existing.add(str(s).lower().strip())

                data["required"]["skills"][bucket] = merged
                data["preferred"]["skills"][bucket] = []

        # Deduplication: Remove any skills from preferred that are already in required
        # Build set of all required skills (lowercased, across all buckets)
        required_flat = set()
        for bucket in BUCKETS:
            for s in data["required"]["skills"].get(bucket, []):
                if s:
                    required_flat.add(str(s).lower().strip())
        
        # Filter preferred skills to remove duplicates
        for bucket in BUCKETS:
            preferred_list = data["preferred"]["skills"].get(bucket, [])
            filtered = [
                s for s in preferred_list
                if s and str(s).lower().strip() not in required_flat
            ]
            data["preferred"]["skills"][bucket] = filtered
        
        return data
    except json.JSONDecodeError:
        print("⚠️ JSON decoding failed, raw response:", file=sys.stderr)
        print(raw, file=sys.stderr)
        raise


# CLI interface (only runs when script is executed directly)
def main():
    # --- Step 1: CLI args ---
    if len(sys.argv) < 2:
        print("❌ Please provide a job description .txt file as an argument.")
        print("Example: python extract_job_skills.py job_description.txt")
        sys.exit(1)
    file_name = sys.argv[1]
    
    # --- Step 2: Read the input file ---
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            jd_text = f.read()
    except FileNotFoundError:
        print(f"❌ File '{file_name}' not found.")
        sys.exit(1)
    
    # --- Step 3: Extract skills ---
    try:
        data = extract_job_skills_from_text(jd_text)
        
        # --- Step 4: Save JSON to file ---
        output_file = os.path.splitext(file_name)[0] + "_skills.json"
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2, ensure_ascii=False)
        
        # Output JSON ONLY to stdout (for programmatic use)
        # Send informative messages to stderr instead so they don't interfere with JSON parsing
        json_output = json.dumps(data, indent=2, ensure_ascii=False)
        print(json_output, file=sys.stdout)
        print(f"✅ Skills data saved to: {output_file}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error extracting skills: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
