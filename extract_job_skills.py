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
        data = ensure_schema(data)
        print(json.dumps(data, indent=2, ensure_ascii=False))

        output_file = os.path.splitext(file_name)[0] + "_skills.json"
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2, ensure_ascii=False)
        print(f"✅ Skills data saved to: {output_file}")
    except json.JSONDecodeError:
        print("⚠️ JSON decoding failed, raw response:")
        print(raw)

if __name__ == "__main__":
    main()
