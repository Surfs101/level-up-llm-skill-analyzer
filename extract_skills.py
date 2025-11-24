# extract_resume_skills.py
import os
import sys
import json
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI

# Shared normalization
from skill_normalization import (
    BUCKETS,
    canonicalize_skills_by_bucket,
    canonicalize_skill_name,
)

# Load environment variables
load_dotenv()


def ensure_resume_schema(skills_block: Dict) -> Dict:
    """
    Ensure the 'skills' block has all 3 buckets:
    ProgrammingLanguages, FrameworksLibraries, ToolsPlatforms.
    """
    out = {}
    skills = skills_block or {}
    for b in BUCKETS:
        v = skills.get(b, [])
        out[b] = v if isinstance(v, list) else []
    return out


def extract_resume_skills_from_text(resume_text: str) -> dict:
    """
    Extract ALL learnable skills from a resume using OpenAI, similar to
    extract_job_skills_from_text but with a single 'skills' block and NO
    required/preferred split.

    Returns:
        {
          "skills": {
            "ProgrammingLanguages": [...],
            "FrameworksLibraries": [...],
            "ToolsPlatforms": [...]
          },
          "courses": [
            "Machine Learning",
            "Deep Learning",
            ...
          ]
        }
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are an expert résumé parser.

Your job is to extract ONLY learnable technical skills and courses that are actually mentioned in the résumé text below.

Learnable skills are technologies, tools, languages, frameworks, libraries, and fields that can be taught through courses, tutorials, or documentation.

ONLY EXTRACT:
- Programming languages (Python, Java, C, C++, R, JavaScript, Go, Rust, etc.)
- Frameworks and libraries (React, Angular, Vue, PyTorch, TensorFlow, scikit-learn, pandas, NumPy, etc.)
- Tools and platforms (Git, Docker, Kubernetes, AWS, Azure, GCP, Databricks, Snowflake, PostgreSQL, MongoDB, MySQL, etc.)
- Databases (PostgreSQL, MongoDB, MySQL, Redis, Elasticsearch, etc.)
- Domain expertise fields (Machine Learning, Deep Learning, Data Science, Artificial Intelligence, Large Language Models, NLP / Natural Language Processing, Computer Vision, RAG / Retrieval-Augmented Generation, Agentic AI, MLOps, LLMOps, etc.)
- Specific technologies and libraries (OpenAI API, LangChain, etc.)

CRITICAL – DO NOT EXTRACT:
1. Generic terms or role descriptions:
   - "Full-stack development", "Full Stack", "Java Full Stack", "Full Stack Developer"
   - "Web Development", "Software Development", "Application Development" (unless it includes a specific technology)
   - "Backend Development", "Frontend Development" (unless tied to a specific technology)
   - Generic job titles like "Developer", "Engineer", "Specialist" without explicit technologies

2. Processes, methodologies, or operational concepts (NOT learnable skills by themselves):
   - ML pipeline automation, model versioning, production deployment
   - Autonomous reasoning, multi-step task execution, external tool integration
   - API integration (the concept; DO extract specific APIs like "OpenAI API")
   - Document pipelines, monitoring, observability, drift detection, alerting
   - Automated testing (the concept; DO extract specific tools like "Jest", "pytest")
   - CI/CD (the concept; DO extract tools like "Jenkins", "GitHub Actions", "CircleCI")
   - Any description of workflow or process rather than a specific technology

3. Normalize skill variations to standard names:
   - "CSS3", "CSS 3", "CSS-3" → "CSS"
   - "HTML5", "HTML 5", "HTML-5" → "HTML"
   - "JavaScript", "JS", "ECMAScript" → "JavaScript"
   - "Node.js", "NodeJS", "Node" → "Node.js"
   - "AI", "Artificial Intelligence" → "Artificial Intelligence"
   - "ML" → "Machine Learning"
   - "DL" → "Deep Learning"
   - "LLM", "Large Language Model", "Large Language Models" → "Large Language Models"
   - "NLP", "Natural Language Processing" → "Natural Language Processing"
   - "CV", "Computer Vision" → "Computer Vision"
   - "RAG", "Retrieval-Augmented Generation" → "Retrieval-Augmented Generation"
   - "Agentic AI", "AI Agency" → "Agentic AI"
   - "DS", "Data Science" → "Data Science"
   Apply these normalizations consistently and always use the canonical full form.

CRITICAL – Extract skills from ALL résumé sections:

1. Project titles / headers:
   - "Machine Learning Image Classifier" → Machine Learning (and possibly Computer Vision)
   - "React E-commerce Web App" → React
   - "Python REST API with Docker" → Python, Docker

2. Job titles in Work Experience:
   - "Python Developer" → Python
   - "Machine Learning Engineer" → Machine Learning
   - "React Frontend Developer" → React
   - "Full Stack Developer (Node.js, React)" → Node.js, React
   - "AI/ML Engineer" → Artificial Intelligence, Machine Learning
   Do NOT extract generic "Developer", "Engineer", etc. without specific technologies.

3. Abbreviations:
   - If the resume uses abbreviations like "LLM", "ML", "DL", "NLP", "CV", "RAG", "RL", "SL", "UL",
     extract them as their full normalized forms using the rules above.

ALSO extract COURSES and CERTIFICATIONS:

- Courses from sections like "Relevant Coursework", "Courses", "Coursework", "Academic Courses", etc.
  Examples: "Machine Learning", "Deep Learning", "Data Science", "Computer Vision", "Software Engineering".
- Online courses:
  e.g., "Machine Learning by Andrew Ng", "Deep Learning Specialization", "Python for Data Science".
- Certifications from sections like "Certifications", "Licenses & Certifications".
  e.g., "AWS Certified Solutions Architect", "Google Cloud Professional", "Microsoft Azure Certified".
- Training programs or bootcamps.

Classify skills into:
- ProgrammingLanguages: specific programming languages.
- FrameworksLibraries: frameworks, libraries, and domain expertise fields (Machine Learning, Deep Learning, Artificial Intelligence, Large Language Models, NLP, Computer Vision, Data Science, RAG, Agentic AI, MLOps, etc.).
- ToolsPlatforms: tools, platforms, cloud providers, databases, analytics tools, DevOps tools, etc.

Output must be STRICT JSON only in this format:
{{
  "skills": {{
    "ProgrammingLanguages": ["Python", "SQL"],
    "FrameworksLibraries": ["React", "scikit-learn", "Machine Learning", "Deep Learning"],
    "ToolsPlatforms": ["Git", "Docker"]
  }},
  "courses": [
    "Machine Learning",
    "Deep Learning",
    "Data Science",
    "Computer Vision",
    "Software Engineering",
    "Machine Learning by Andrew Ng",
    "Deep Learning Specialization",
    "AWS Certified Solutions Architect",
    "Google Cloud Professional"
  ]
}}

Resume:
{resume_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    except Exception as e:
        error_msg = str(e)
        raise Exception(f"Error calling OpenAI API for resume skill extraction: {error_msg}")

    raw = response.choices[0].message.content
    try:
        llm_data = json.loads(raw)
        # Ensure schema and canonicalize
        skills_raw = llm_data.get("skills", {}) or {}
        skills_block = ensure_resume_schema(skills_raw)
        skills_canon = canonicalize_skills_by_bucket(skills_block)
        courses = llm_data.get("courses", []) or []

        return {
            "skills": skills_canon,
            "courses": courses,
        }
    except json.JSONDecodeError:
        print("⚠️ JSON decoding failed, raw response:", file=sys.stderr)
        print(raw, file=sys.stderr)
        raise


# --- CLI interface (like extract_job_skills.py) ---
def main():
    if len(sys.argv) < 2:
        print("❌ Please provide a resume .txt file as an argument.")
        print("Example: python extract_resume_skills.py resume_cleaned.txt")
        sys.exit(1)

    file_name = sys.argv[1]

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            resume_text = f.read()
    except FileNotFoundError:
        print(f"❌ File '{file_name}' not found.")
        sys.exit(1)

    try:
        data = extract_resume_skills_from_text(resume_text)

        output_file = os.path.splitext(file_name)[0] + "_skills.json"
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(data, out_f, indent=2, ensure_ascii=False)

        json_output = json.dumps(data, indent=2, ensure_ascii=False)
        print(json_output, file=sys.stdout)
        print(f"✅ Skills data saved to: {output_file}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error extracting resume skills: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
