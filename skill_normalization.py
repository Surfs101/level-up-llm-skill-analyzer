# skill_normalization.py
# Single source of truth for skill normalization and canonicalization

from typing import Dict, List

# Canonical mapping from various forms → a single standard name
CANONICAL_SKILL_MAP = {
    # Programming languages
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "python-3": "Python",
    "py": "Python",

    "javascript": "JavaScript",
    "js": "JavaScript",
    "ecmascript": "JavaScript",

    "html": "HTML",
    "html5": "HTML",
    "html 5": "HTML",
    "html-5": "HTML",

    "css": "CSS",
    "css3": "CSS",
    "css 3": "CSS",
    "css-3": "CSS",

    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",

    "c": "C",
    "c++": "C++",
    "c#": "C#",

    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",

    # ML / AI / Data domains
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "machine-learning": "Machine Learning",
    "m.l.": "Machine Learning",

    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "artificial-intelligence": "Artificial Intelligence",

    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "deep-learning": "Deep Learning",

    "data science": "Data Science",
    "data scientist": "Data Science",
    "data-science": "Data Science",
    "ds": "Data Science",

    "data analytics": "Data Analytics",
    "data analyst": "Data Analytics",
    "data-analytics": "Data Analytics",

    "mlops": "MLOps",
    "ml ops": "MLOps",
    "machine learning ops": "MLOps",
    "m.l.ops": "MLOps",

    "llm": "Large Language Models",
    "large language model": "Large Language Models",
    "large language models": "Large Language Models",

    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",

    "cv": "Computer Vision",
    "computer vision": "Computer Vision",

    "rag": "Retrieval-Augmented Generation",
    "retrieval-augmented generation": "Retrieval-Augmented Generation",

    "agentic ai": "Agentic AI",
    "ai agency": "Agentic AI",

    # Frameworks / libs / tools / clouds
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",

    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",

    "pytorch": "PyTorch",
    "torch": "PyTorch",

    "aws": "AWS",
    "amazon web services": "AWS",

    "azure": "Azure",
    "microsoft azure": "Azure",

    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",

    "git": "Git",
    "github": "GitHub",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "redis": "Redis",
}

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]


def canonicalize_skill_name(skill: str) -> str:
    """
    Canonicalize a skill name to its standard form.
    
    Args:
        skill: Raw skill name (e.g., "JS", "LLM", "html5")
    
    Returns:
        Canonical skill name (e.g., "JavaScript", "Large Language Models", "HTML")
    """
    if not skill:
        return ""
    normalized = str(skill).strip()
    key = normalized.lower()
    return CANONICAL_SKILL_MAP.get(key, normalized)


def canonicalize_skills_by_bucket(skills_dict: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Given a dict {bucket: [skills]}, return a new dict where:
    - bucket names are preserved
    - each skill is canonicalized
    - duplicates (case-insensitive) within a bucket are removed
    
    Args:
        skills_dict: Dictionary mapping bucket names to lists of skill names
    
    Returns:
        Dictionary with canonicalized skills, duplicates removed
    """
    if not isinstance(skills_dict, dict):
        return {b: [] for b in BUCKETS}

    # Include all existing buckets + the standard BUCKETS list
    buckets = set(BUCKETS) | set(skills_dict.keys())
    canonicalized = {}

    for bucket in buckets:
        seen = set()
        canonicalized[bucket] = []
        for raw_skill in (skills_dict.get(bucket) or []):
            canonical = canonicalize_skill_name(raw_skill)
            key = canonical.lower()
            if key and key not in seen:
                canonicalized[bucket].append(canonical)
                seen.add(key)

    return canonicalized


def normalize_to_full_form_for_output(skill: str) -> str:
    """
    For output (reports, UI), ensure skill has nice casing.
    Since canonicalize_skill_name already returns a nicely cased name
    when possible, we just call it and then ensure it is stripped.
    
    Args:
        skill: Skill name to normalize
    
    Returns:
        Normalized skill name with proper casing
    """
    return canonicalize_skill_name(skill).strip()

