import os
import re
import json
import sys
from typing import List, Dict, Set
from openai import OpenAI
from dotenv import load_dotenv

# --- Step 1: Read .env file for API key ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Step 2: Get file name from command line ---
if len(sys.argv) < 2:
    print("❌ Please provide a text file name as an argument.")
    print("Example: python extract_skills.py resume_cleaned.txt")
    sys.exit(1)

file_name = sys.argv[1]

# --- Step 3: Read the input file ---
try:
    with open(file_name, "r", encoding="utf-8") as f:
        resume_text = f.read()
except FileNotFoundError:
    print(f"❌ File '{file_name}' not found.")
    sys.exit(1)

# -------------------------
# Rule-based augmentation
# -------------------------

KNOWN_LANGUAGES = {
    "python","java","c","c++","c#","javascript","typescript","go","rust","ruby","php","sql","scala","kotlin","swift","r","matlab"
}
KNOWN_FRAMEWORKS = {
    "react","angular","vue","django","flask","spring","fastapi","pytorch","tensorflow","keras","scikit-learn","sklearn","pandas","numpy","opencv","spark","hadoop","airflow","dbt","next.js","node.js","express","laravel",".net","dotnet","rails","bootstrap","tailwind css","material ui",
    # Machine Learning & AI Domain Terms
    "machine learning","deep learning","artificial intelligence","ai","ml","dl","neural networks","cnn","rnn","nlp","natural language processing",
    "computer vision","cv","data science","data analytics","predictive modeling","reinforcement learning","supervised learning","unsupervised learning",
    "transfer learning","feature engineering","model training","model evaluation","mlops","data engineering","big data","data mining"
}

def load_extra_vocab() -> Set[str]:
    """Optionally load extra skills from skills_vocab.txt (one per line)."""
    vocab_path = "skills_vocab.txt"
    extra: Set[str] = set()
    if os.path.exists(vocab_path):
        try:
            with open(vocab_path, "r", encoding="utf-8") as f:
                for line in f:
                    term = line.strip()
                    if term:
                        extra.add(term)
        except Exception:
            pass
    return extra

def find_terms_in_text(terms: List[str], text: str) -> Set[str]:
    """Find terms in text with approximate word-boundary matching, return original-cased hits."""
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
    # Domain expertise terms that should be extracted as skills
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
    
    base_vocab = set().union(KNOWN_LANGUAGES, KNOWN_FRAMEWORKS, DOMAIN_TERMS, {
        "git","github","gitlab","docker","kubernetes","aws","gcp","azure","sagemaker","vertex ai","bigquery","databricks","mlflow","airbyte","snowflake","postgres","mysql","mongodb","redis","elasticsearch","tableau","power bi","looker","jira","confluence","jenkins","circleci","terraform","ansible"
    })
    base_vocab |= load_extra_vocab()
    hits = find_terms_in_text(sorted(base_vocab, key=len, reverse=True), text)

    def bucketize(term: str) -> str:
        t = term.lower()
        if t in KNOWN_LANGUAGES:
            return "ProgrammingLanguages"
        # Check if it's a domain/ML term (should go in FrameworksLibraries)
        domain_terms = {
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
        if t in domain_terms or t in KNOWN_FRAMEWORKS:
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
    out: Dict[str, List[str]] = {k: [] for k in ["ProgrammingLanguages","FrameworksLibraries","ToolsPlatforms"]}
    for b in out.keys():
        llm_list = llm_obj.get(b, []) if isinstance(llm_obj, dict) else []
        rule_list = rule_obj.get(b, []) if isinstance(rule_obj, dict) else []
        # Preserve insertion order, prefer original-cased items from text
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

# --- Step 4: Create prompt ---
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

# --- Step 5: Call GPT ---
response = client.chat.completions.create(
    model="gpt-4o",  # best model available now
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

# --- Step 6: Handle response safely ---
raw = response.choices[0].message.content

try:
    skills_data = json.loads(raw)
    # Rule-based pass for recall boost
    rule_based = rule_based_extract(resume_text)
    merged = {"skills": merge_outputs(skills_data.get("skills", {}), rule_based)}
    print(json.dumps(merged, indent=2, ensure_ascii=False))

    # --- Step 7: Save JSON to file ---
    output_file = os.path.splitext(file_name)[0] + "_skills.json"
    with open(output_file, "w", encoding="utf-8") as out_f:
        json.dump(merged, out_f, indent=2, ensure_ascii=False)
    print(f"✅ Skills data saved to: {output_file}")

except json.JSONDecodeError:
    print("⚠️ JSON decoding failed, raw response:")
    print(raw)
