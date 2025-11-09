# extract_job_skills.py
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]

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
{jd_text}
""".strip()

    # --- Step 5: Call GPT (same model + response_format as resume extractor) ---
    response = client.chat.completions.create(
        model="gpt-4o",
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
