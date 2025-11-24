# score_skills_match.py
# Compare resume_*_skills.json vs job_description_*_skills.json and compute coverage scores.
#
# Outputs:
#   scores_out/skills_match_<slug>.json
#   scores_out/skills_match_<slug>.md
#
# Usage (PowerShell one line):
#   python score_skills_match.py --resume "C:\path\resume_cleaned_skills.json" --job "C:\path\job_description_skills.json" --label "MLOps Engineer"
#
# Optional weights:
#   --weights "required=1.0,preferred=0.5"
#
# Notes:
# - Case-insensitive matching for skills (compares lowercased), but outputs original-cased examples where possible.

import os
import json
import argparse
import re
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

# Import shared normalization
from skill_normalization import (
    BUCKETS,
    canonicalize_skill_name,
    canonicalize_skills_by_bucket,
    normalize_to_full_form_for_output,
)

# Load environment variables
load_dotenv()

TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]

# Importance weights per bucket (higher → more important for gap closure)
BUCKET_WEIGHTS = {
    "ToolsPlatforms": 1.0,
    "FrameworksLibraries": 0.9,
    "ProgrammingLanguages": 0.8,
}

# -------------------------
# Helpers
# -------------------------
def load_json(p: str) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def slugify(s: str) -> str:
    s = (s or "role").lower()
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, ' ')
    return "_".join([t for t in s.split() if t])

# normalize_skill_name and normalize_to_full_form are now imported from skill_normalization
# For matching, we use canonicalize_skill_name and compare lowercase
# For output, we use normalize_to_full_form_for_output


def flatten_and_canonicalize(skills_by_bucket: dict) -> list:
    """
    Flatten skills from all buckets into a single canonicalized list.
    Used for gathering all resume skills or job skills before matching.
    
    Args:
        skills_by_bucket: Dictionary mapping bucket names to lists of skills
    
    Returns:
        Sorted list of unique canonicalized skill names
    """
    out = []
    for bucket, skills in (skills_by_bucket or {}).items():
        for s in skills or []:
            canon = canonicalize_skill_name(s)
            if canon:
                out.append(canon)
    return sorted(set(out), key=str.lower)


def to_set_safe(d: dict, bucket: str):
    """Convert skills list to normalized lowercase set for intelligent comparison."""
    if not isinstance(d, dict):
        return set()
    v = d.get(bucket, [])
    if not isinstance(v, list):
        return set()
    # Normalize each skill before adding to set to ensure abbreviations match full forms
    normalized_skills = set()
    for x in v:
        if isinstance(x, str) and x.strip():
            # Use canonicalize_skill_name and then lowercase for comparison
            normalized = canonicalize_skill_name(x).lower()
            normalized_skills.add(normalized)
    return normalized_skills

def parse_weights(s: str):
    # format: "required=1.0,preferred=0.5"
    req, pref = 1.0, 0.5
    if not s:
        return req, pref
    parts = [x.strip() for x in s.split(",") if x.strip()]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip().lower()
            try:
                val = float(v.strip())
            except:
                continue
            if k == "required": req = val
            if k == "preferred": pref = val
    return req, pref

def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d > 0 else 0.0

def match_and_rank_skills_with_llm(
    resume_skills: dict,
    job_required_skills: dict,
    job_preferred_skills: dict,
    job_description_text: str
) -> dict:
    """
    Use LLM to perform smart matching and ranking of skills.
    
    The LLM will:
    1. Perform smart matching (recognizes AI = Artificial Intelligence, HTML = HTML5, etc.)
    2. Identify covered vs missing skills
    3. Rank missing skills by priority (most critical first)
    
    Args:
        resume_skills: Resume skills by bucket
        job_required_skills: Job required skills by bucket
        job_preferred_skills: Job preferred skills by bucket
        job_description_text: Full job description text
    
    Returns:
        Dictionary with:
        - "covered_required": List of covered required skills
        - "missing_required": List of missing required skills (ranked by priority)
        - "covered_preferred": List of covered preferred skills
        - "missing_preferred": List of missing preferred skills (ranked by priority)
        - "skill_priorities": Dict mapping skill names to priority weights (0.0-1.0)
    """
    if not job_description_text:
        # Fallback to simple matching if no job description
        resume_all = set()
        job_req_all = set()
        job_pref_all = set()
        for b in BUCKETS:
            resume_all.update(to_set_safe(resume_skills, b))
            job_req_all.update(to_set_safe(job_required_skills, b))
            job_pref_all.update(to_set_safe(job_preferred_skills, b))
        
        missing_req = sorted(list(job_req_all - resume_all))
        missing_pref = sorted(list(job_pref_all - resume_all))
        covered_req = sorted(list(resume_all & job_req_all))
        covered_pref = sorted(list(resume_all & job_pref_all))
        
        return {
            "covered_required": covered_req,
            "missing_required": missing_req,
            "covered_preferred": covered_pref,
            "missing_preferred": missing_pref,
            "skill_priorities": {s: 0.5 for s in missing_req + missing_pref}
        }
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Prepare skills data for LLM
    resume_skills_str = json.dumps(resume_skills, indent=2, ensure_ascii=False)
    job_required_str = json.dumps(job_required_skills, indent=2, ensure_ascii=False)
    job_preferred_str = json.dumps(job_preferred_skills, indent=2, ensure_ascii=False)
    
    prompt = f"""You are an expert skill matcher and prioritizer.

TASK:
1. Match resume skills against job skills using INTELLIGENT matching:
   - Recognize synonyms and variations (e.g., "AI" = "Artificial Intelligence", "HTML5" = "HTML", "CSS3" = "CSS", "ML" = "Machine Learning")
   - Normalize all variations and abbreviations to standard names:
     * Programming/Languages:
       - "CSS3", "CSS 3", "CSS-3" → "CSS"
       - "HTML5", "HTML 5", "HTML-5" → "HTML"
       - "JavaScript", "JS", "ECMAScript" → "JavaScript"
       - "Node.js", "NodeJS", "Node" → "Node.js"
     * AI/ML Domain (CRITICAL - abbreviations must match full forms):
       - "AI", "Artificial Intelligence" → "Artificial Intelligence"
       - "ML", "Machine Learning" → "Machine Learning"
       - "DL", "Deep Learning" → "Deep Learning"
       - "LLM", "Large Language Models", "Large Language Model" → "Large Language Models"
       - "NLP", "Natural Language Processing" → "Natural Language Processing"
       - "CV", "Computer Vision" → "Computer Vision"
       - "RAG", "Retrieval-Augmented Generation" → "Retrieval-Augmented Generation"
       - "Agentic AI", "AI Agency" → "Agentic AI"
       - "MLOps", "Machine Learning Operations" → "MLOps"
     * Data Domain:
       - "DS", "Data Science" → "Data Science"
   - Handle different casing, spacing, and formatting
   - Understand that skills can be equivalent even if written differently (e.g., "ML" matches "Machine Learning", "LLM" matches "Large Language Models")
   - IGNORE generic terms like "Full-stack development", "Java Full Stack", "Full Stack Developer" - these are not concrete skills
   
   CRITICAL: When comparing skills, treat abbreviations and their full forms as EQUIVALENT:
   - If job requires "Machine Learning" and resume has "ML" → COVERED
   - If job requires "LLM" and resume has "Large Language Models" → COVERED
   - If job requires "Artificial Intelligence" and resume has "AI" → COVERED
   - Apply normalization consistently to ensure accurate matching

2. Identify which skills are COVERED (resume has them) and which are MISSING (resume lacks them)
   - Use normalized skill names for comparison

3. Rank missing skills by PRIORITY based on the job description:
   - Most critical/most emphasized skills first
   - Consider frequency of mention, importance to role, emphasis in description
   - Return priority weights (0.0-1.0) where 1.0 = most critical

RESUME SKILLS:
{resume_skills_str}

JOB REQUIRED SKILLS:
{job_required_str}

JOB PREFERRED SKILLS:
{job_preferred_str}

JOB DESCRIPTION:
{job_description_text[:2000] if len(job_description_text) > 2000 else job_description_text}

Return JSON in this format:
{{
  "covered_required": ["Python", "Docker", ...],
  "missing_required": ["Kubernetes", "Machine Learning", ...],  // Ranked by priority (most critical first)
  "covered_preferred": ["Java", ...],
  "missing_preferred": ["TensorFlow", ...],  // Ranked by priority
  "skill_priorities": {{
    "Kubernetes": 0.95,
    "Machine Learning": 0.85,
    "TensorFlow": 0.70,
    ...
  }}
}}

CRITICAL: 
- Use intelligent matching (AI = Artificial Intelligence, HTML5 = HTML, etc.)
- Rank missing_required and missing_preferred by priority (most critical first)
- skill_priorities should include all missing skills with weights 0.0-1.0"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Faster and cheaper for matching
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            raise Exception(f"OpenAI API quota exceeded. Please check your billing and plan. Error: {error_msg}")
        else:
            raise Exception(f"Error calling OpenAI API for skill matching: {error_msg}")
    
    try:
        result = json.loads(response.choices[0].message.content)
        
        # Ensure all fields exist
        return {
            "covered_required": result.get("covered_required", []),
            "missing_required": result.get("missing_required", []),
            "covered_preferred": result.get("covered_preferred", []),
            "missing_preferred": result.get("missing_preferred", []),
            "skill_priorities": result.get("skill_priorities", {})
        }
        
    except Exception as e:
        print(f"Warning: LLM skill matching failed: {e}. Falling back to simple matching.")
        # Fallback to simple matching
        resume_all = set()
        job_req_all = set()
        job_pref_all = set()
        for b in BUCKETS:
            resume_all.update(to_set_safe(resume_skills, b))
            job_req_all.update(to_set_safe(job_required_skills, b))
            job_pref_all.update(to_set_safe(job_preferred_skills, b))
        
        missing_req = sorted(list(job_req_all - resume_all))
        missing_pref = sorted(list(job_pref_all - resume_all))
        covered_req = sorted(list(resume_all & job_req_all))
        covered_pref = sorted(list(resume_all & job_pref_all))
        
        return {
            "covered_required": covered_req,
            "missing_required": missing_req,
            "covered_preferred": covered_pref,
            "missing_preferred": missing_pref,
            "skill_priorities": {s: 0.5 for s in missing_req + missing_pref}
        }

# Keep an original-casing registry so we can display nicer names in outputs
def build_original_case_map(*lists):
    m = {}
    for lst in lists:
        for s in lst:
            if isinstance(s, str) and s.strip():
                low = s.strip().lower()
                if low not in m:
                    m[low] = s.strip()
    return m

# -------------------------
# Scoring
# -------------------------
def score_match(resume_json: dict, job_json: dict, w_required: float, w_preferred: float, job_description_text: str = ""):
    resume_sk = resume_json.get("skills", {}) or {}
    job_req_sk = (job_json.get("required", {}) or {}).get("skills", {}) or {}
    job_pref_sk = (job_json.get("preferred", {}) or {}).get("skills", {}) or {}

    # For pretty outputs, gather all original skills to map back case
    orig_map = build_original_case_map(
        *[resume_sk.get(b, []) for b in BUCKETS],
        *[job_req_sk.get(b, []) for b in BUCKETS],
        *[job_pref_sk.get(b, []) for b in BUCKETS],
    )

    # Use LLM only for smart ranking / priorities (not for deciding which skills exist)
    llm_results = match_and_rank_skills_with_llm(
        resume_sk, job_req_sk, job_pref_sk, job_description_text
    )
    skill_priorities = llm_results.get("skill_priorities", {}) or {}

    # --- Deterministic coverage from normalized sets ---
    # Build normalized sets for resume, required, and preferred skills
    resume_all = set()
    job_req_all = set()
    job_pref_all = set()
    for b in BUCKETS:
        resume_all.update(to_set_safe(resume_sk, b))
        job_req_all.update(to_set_safe(job_req_sk, b))
        job_pref_all.update(to_set_safe(job_pref_sk, b))

    # Set-based coverage (bucket-agnostic)
    raw_covered_required = job_req_all & resume_all
    raw_missing_required = job_req_all - resume_all
    raw_covered_preferred = job_pref_all & resume_all
    raw_missing_preferred = job_pref_all - resume_all

    # Helper: sort a list of missing skills by LLM priority (highest first)
    def sort_by_priority(skills):
        def priority_key(s: str):
            # Try exact key, then normalized key, default 0.5
            base = skill_priorities.get(s, skill_priorities.get(canonicalize_skill_name(s).lower(), 0.5))
            # negative because we want descending order
            return -base
        # Preserve input order as tiebreaker by using enumerate
        return [skill for _, skill in sorted(
            [(i, s) for i, s in enumerate(skills)],
            key=lambda pair: (priority_key(pair[1]), pair[0])
        )]

    # Convert sets → ordered lists
    covered_required_all = sorted(list(raw_covered_required))
    covered_preferred_all = sorted(list(raw_covered_preferred))
    missing_required_all = sort_by_priority(list(raw_missing_required))
    missing_preferred_all = sort_by_priority(list(raw_missing_preferred))

    # Compute per-bucket stats (still needed for detailed breakdown)
    per_bucket = {}
    total_req_needed = 0
    total_req_covered = 0
    total_pref_needed = 0
    total_pref_covered = 0

    for b in BUCKETS:
        have = to_set_safe(resume_sk, b)
        need_req = to_set_safe(job_req_sk, b)
        need_pref = to_set_safe(job_pref_sk, b)

        covered_req = sorted(list(have & need_req))
        missing_req_raw = list(need_req - have)
        covered_pref = sorted(list(have & need_pref))
        missing_pref_raw = list(need_pref - have)

        req_total = len(need_req)
        pref_total = len(need_pref)

        total_req_needed += req_total
        total_pref_needed += pref_total
        total_req_covered += len(covered_req)
        total_pref_covered += len(covered_pref)

        per_bucket[b] = {
            "required": {
                "total": req_total,
                "covered": len(covered_req),
                "coverage_pct": pct(len(covered_req), req_total),
                "covered_skills": [orig_map.get(s, s) for s in covered_req],
                "missing_skills": [orig_map.get(s, s) for s in missing_req_raw],
            },
            "preferred": {
                "total": len(need_pref),
                "covered": len(covered_pref),
                "coverage_pct": pct(len(covered_pref), len(need_pref)),
                "covered_skills": [orig_map.get(s, s) for s in covered_pref],
                "missing_skills": [orig_map.get(s, s) for s in missing_pref_raw],
            }
        }

    # Overall coverages using deterministic set-based matching
    # Total should be covered + missing (all job-required/preferred skills are accounted for)
    req_cov_bucket_agnostic = len(covered_required_all)
    pref_cov_bucket_agnostic = len(covered_preferred_all)
    req_total_bucket_agnostic = req_cov_bucket_agnostic + len(missing_required_all)
    pref_total_bucket_agnostic = pref_cov_bucket_agnostic + len(missing_preferred_all)
    req_cov_pct = pct(req_cov_bucket_agnostic, req_total_bucket_agnostic) if req_total_bucket_agnostic > 0 else 0.0
    pref_cov_pct = pct(pref_cov_bucket_agnostic, pref_total_bucket_agnostic) if pref_total_bucket_agnostic > 0 else 0.0

    # Weighted score
    # Normalize by weights present (if a section has 0 required skills, don't penalize)
    weight_den = 0.0
    weighted_sum = 0.0
    if req_total_bucket_agnostic > 0:
        weighted_sum += w_required * (req_cov_bucket_agnostic / req_total_bucket_agnostic)
        weight_den += w_required
    if pref_total_bucket_agnostic > 0:
        weighted_sum += w_preferred * (pref_cov_bucket_agnostic / pref_total_bucket_agnostic)
        weight_den += w_preferred
    weighted_score = round(100.0 * (weighted_sum / weight_den), 2) if weight_den > 0 else 0.0

    # Jaccard overall (resume vs job required+preferred)
    # Use normalized sets for smart matching
    all_resume_skills = set()
    all_job_skills = set()
    for b in BUCKETS:
        all_resume_skills.update(to_set_safe(resume_sk, b))
        all_job_skills.update(to_set_safe(job_req_sk, b))
        all_job_skills.update(to_set_safe(job_pref_sk, b))
    
    # For Jaccard, use simple set operations on normalized sets (canonicalization handles smart matching)
    inter = len(all_resume_skills & all_job_skills)
    uni = len(all_resume_skills | all_job_skills)
    jaccard_pct = pct(inter, uni)

    # Extra skills on resume not mentioned in job (could be nice-to-have)
    extra_resume = sorted(list(all_resume_skills - all_job_skills))
    extra_resume = [orig_map.get(s, s) for s in extra_resume]

    # Build structured gaps by bucket (for TARGET_BUCKETS only) - use deterministically computed missing skills
    gaps_required_structured = {}
    gaps_preferred_structured = {}
    for b in TARGET_BUCKETS:
        have = to_set_safe(resume_sk, b)
        need_req = to_set_safe(job_req_sk, b)
        need_pref = to_set_safe(job_pref_sk, b)
        # Filter deterministically computed missing skills (sorted by LLM priority) to this bucket
        gaps_required_structured[b] = [
            s for s in missing_required_all 
            if str(s).lower().strip() in [str(sk).lower().strip() for sk in (need_req - have)]
        ]
        gaps_preferred_structured[b] = [
            s for s in missing_preferred_all 
            if str(s).lower().strip() in [str(sk).lower().strip() for sk in (need_pref - have)]
        ]

    # Normalize missing skills to full forms for consistent output to course/project recommenders
    # This ensures "ML" becomes "Machine Learning", "LLM" becomes "Large Language Models", etc.
    # Normalization happens AFTER matching/comparison, so the output has standardized names
    normalized_missing_required = [normalize_to_full_form_for_output(s) for s in missing_required_all]
    normalized_missing_preferred = [normalize_to_full_form_for_output(s) for s in missing_preferred_all]
    
    # Use skill priorities from LLM (already computed in match_and_rank_skills_with_llm)
    # Map priorities using normalized skill names (full forms)
    skill_priorities_dict = {"required": {}, "preferred": {}}
    for i, skill in enumerate(missing_required_all):
        normalized_skill = normalized_missing_required[i]
        # Try to get priority from original skill name or normalized name
        priority = skill_priorities.get(skill, skill_priorities.get(canonicalize_skill_name(skill).lower(), 0.5))
        skill_priorities_dict["required"][normalized_skill] = priority
    for i, skill in enumerate(missing_preferred_all):
        normalized_skill = normalized_missing_preferred[i]
        # Try to get priority from original skill name or normalized name
        priority = skill_priorities.get(skill, skill_priorities.get(canonicalize_skill_name(skill).lower(), 0.5))
        skill_priorities_dict["preferred"][normalized_skill] = priority

    # Calculate final skill weights (bucket weight × LLM priority × multiplier for top 3)
    # This combines all prioritization logic so recommend_courses.py just uses the weights
    skill_weights_final = {"required": {}, "preferred": {}}
    
    for priority_type in ["required", "preferred"]:
        missing_skills_list = normalized_missing_required if priority_type == "required" else normalized_missing_preferred
        original_list = missing_required_all if priority_type == "required" else missing_preferred_all
        priorities_to_use = skill_priorities_dict[priority_type]
        
        if not missing_skills_list:
            skill_weights_final[priority_type] = {}
            continue
        
        # Skills are deterministically computed; order sorted by LLM priority
        # Calculate base weights using bucket weights and LLM priorities
        base_weights = {}
        for skill in missing_skills_list:
            # Find which bucket this skill belongs to
            bucket = None
            for b in TARGET_BUCKETS:
                if str(skill).lower().strip() in [str(s).lower().strip() for s in (job_req_sk.get(b, []) if priority_type == "required" else job_pref_sk.get(b, []))]:
                    bucket = b
                    break
            bucket_weight = BUCKET_WEIGHTS.get(bucket, 0.5) if bucket else 0.5
            llm_priority = priorities_to_use.get(skill, 0.5)
            base_weights[skill] = bucket_weight * llm_priority
        
        # Apply multipliers to top 3 skills (deterministically computed, sorted by LLM priority)
        final_weights = {}
        for i, skill in enumerate(missing_skills_list):
            base_weight = base_weights.get(skill, 0.5)
            if i < 3:
                # Top skill gets 3x, 2nd gets 2x, 3rd gets 1.5x
                multiplier = [3.0, 2.0, 1.5][i]
                final_weights[skill] = base_weight * multiplier
            else:
                final_weights[skill] = base_weight
        
        skill_weights_final[priority_type] = final_weights

    summary = {
        "weighted_score": weighted_score,  # 0-100
        "required_coverage_pct": req_cov_pct,
        "preferred_coverage_pct": pref_cov_pct,
        "overall_jaccard_pct": jaccard_pct,
        "counts": {
            "required": {"covered": req_cov_bucket_agnostic, "total": req_total_bucket_agnostic},
            "preferred": {"covered": pref_cov_bucket_agnostic, "total": pref_total_bucket_agnostic}
        },
        "weights_used": {"required": w_required, "preferred": w_preferred}
    }

    # Normalize gaps structured by bucket to full forms
    normalized_gaps_required = {}
    normalized_gaps_preferred = {}
    for b in TARGET_BUCKETS:
        normalized_gaps_required[b] = [normalize_to_full_form_for_output(s) for s in gaps_required_structured.get(b, [])]
        normalized_gaps_preferred[b] = [normalize_to_full_form_for_output(s) for s in gaps_preferred_structured.get(b, [])]
    
    return {
        "summary": summary,
        "by_bucket": per_bucket,
        "covered_skills": {
            "required": sorted(list(set(covered_required_all))),
            "preferred": sorted(list(set(covered_preferred_all)))
        },
        "missing_skills": {
            "required": list(dict.fromkeys(normalized_missing_required)),  # Preserve priority order, remove duplicates, normalized to full forms
            "preferred": list(dict.fromkeys(normalized_missing_preferred))  # Preserve priority order, remove duplicates, normalized to full forms
        },
        "gaps": {
            "required": normalized_gaps_required,  # Normalized to full forms
            "preferred": normalized_gaps_preferred  # Normalized to full forms
        },
        "skill_priorities": skill_priorities_dict,  # Already uses normalized skill names
        "skill_weights": skill_weights_final,  # Already uses normalized skill names - Final weights ready to use (bucket × LLM priority × multiplier)
        "extra_resume_skills": extra_resume
    }

# -------------------------
# Writers
# -------------------------
def dict_to_md_table(d: dict):
    if not d:
        return "_None_"
    lines = ["| Key | Value |", "|---|---|"]
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"| {k} | |")
            for kk, vv in v.items():
                lines.append(f"| └ {kk} | {vv} |")
        else:
            lines.append(f"| {k} | {v} |")
    return "\n".join(lines)

def write_outputs(data: dict, outdir: Path, label: str):
    outdir.mkdir(parents=True, exist_ok=True)
    slug = slugify(label)
    json_path = outdir / f"skills_match_{slug}.json"
    md_path = outdir / f"skills_match_{slug}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Build MD
    md = []
    md.append(f"# Skills Match – {label}\n")
    md.append("## Summary\n")
    md.append(dict_to_md_table(data.get("summary", {})))
    md.append("\n\n## Coverage by Bucket\n")
    for b in BUCKETS:
        sec = data.get("by_bucket", {}).get(b, {})
        if not sec: 
            continue
        md.append(f"### {b}")
        # Required
        req = sec.get("required", {})
        md.append(f"- **Required**: {req.get('covered',0)}/{req.get('total',0)} "
                  f"({req.get('coverage_pct',0)}%)")
        if req.get("covered_skills"):
            md.append(f"  - Covered: {', '.join(req['covered_skills'])}")
        if req.get("missing_skills"):
            md.append(f"  - Missing: {', '.join(req['missing_skills'])}")
        # Preferred
        pref = sec.get("preferred", {})
        md.append(f"- **Preferred**: {pref.get('covered',0)}/{pref.get('total',0)} "
                  f"({pref.get('coverage_pct',0)}%)")
        if pref.get("covered_skills"):
            md.append(f"  - Covered: {', '.join(pref['covered_skills'])}")
        if pref.get("missing_skills"):
            md.append(f"  - Missing: {', '.join(pref['missing_skills'])}")
        md.append("")  # blank

    # Lists
    cov = data.get("covered_skills", {})
    miss = data.get("missing_skills", {})
    extra = data.get("extra_resume_skills", [])

    md.append("\n## Covered Skills (All)\n")
    md.append(f"- Required: {', '.join(cov.get('required', [])) or '-'}")
    md.append(f"- Preferred: {', '.join(cov.get('preferred', [])) or '-'}")

    md.append("\n## Missing Skills (All)\n")
    md.append(f"- Required: {', '.join(miss.get('required', [])) or '-'}")
    md.append(f"- Preferred: {', '.join(miss.get('preferred', [])) or '-'}")

    md.append("\n## Extra Skills on Résumé (Not in JD)\n")
    md.append(f"{', '.join(extra) if extra else '-'}\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")

# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Compute skills match score between resume and job JSONs.")
    parser.add_argument("--resume", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--job", required=True, help="Path to job_description_*_skills.json")
    parser.add_argument("--label", default="Role", help="Short label for output filenames (e.g., 'MLOps Engineer')")
    parser.add_argument("--weights", default="required=1.0,preferred=0.5",
                        help='Weights for sections, e.g., "required=1.0,preferred=0.5"')
    parser.add_argument("--outdir", default="scores_out", help="Output directory")
    args = parser.parse_args()

    resume_json = load_json(args.resume)
    job_json = load_json(args.job)
    w_req, w_pref = parse_weights(args.weights)

    # CLI usage: job_description_text is optional (empty string if not provided)
    # This allows the function to work without LLM priority analysis
    data = score_match(resume_json, job_json, w_req, w_pref, job_description_text="")
    write_outputs(data, Path(args.outdir), args.label)

# -------------------------
# Sanity Check Helper
# -------------------------
def sanity_check_normalization():
    """
    Sanity check to verify that normalization works correctly.
    Tests that resume and job skills with different variations are normalized to the same canonical names.
    """
    print("Running sanity check for skill normalization...")
    
    # Test resume text with variations
    resume_text = """
    Skills: Python, JS, HTML5, CSS3, NodeJS, ML, AI, LLM, NLP, AWS, Docker.
    """
    
    # Test job description text with full forms
    job_text = """
    We look for experience with JavaScript, HTML, CSS, Node.js, Machine Learning, 
    Artificial Intelligence, Large Language Models, Natural Language Processing, AWS, and Docker.
    """
    
    try:
        # Import extraction functions
        from extract_skills import extract_resume_skills_from_text
        from extract_job_skills import extract_job_skills_from_text
        
        # Extract skills
        print("\n1. Extracting skills from resume...")
        resume_json = extract_resume_skills_from_text(resume_text)
        resume_skills = resume_json.get("skills", {})
        
        print("\n2. Extracting skills from job description...")
        job_json = extract_job_skills_from_text(job_text)
        job_required = job_json.get("required", {}).get("skills", {})
        
        print("\n3. Resume skills by bucket (canonicalized):")
        for bucket in BUCKETS:
            skills = resume_skills.get(bucket, [])
            if skills:
                print(f"  {bucket}: {', '.join(skills)}")
        
        print("\n4. Job required skills by bucket (canonicalized):")
        for bucket in BUCKETS:
            skills = job_required.get(bucket, [])
            if skills:
                print(f"  {bucket}: {', '.join(skills)}")
        
        # Score match
        print("\n5. Computing match scores...")
        match_result = score_match(resume_json, job_json, 1.0, 0.5, job_text)
        
        print("\n6. Covered skills:")
        covered = match_result.get("covered_skills", {}).get("required", [])
        print(f"  Required: {', '.join(covered) if covered else 'None'}")
        
        print("\n7. Missing skills:")
        missing = match_result.get("missing_skills", {}).get("required", [])
        print(f"  Required: {', '.join(missing) if missing else 'None'}")
        
        # Verify expected behavior
        print("\n8. Verification:")
        expected_covered = ["JavaScript", "HTML", "CSS", "Node.js", "Machine Learning", 
                           "Artificial Intelligence", "Large Language Models", 
                           "Natural Language Processing", "AWS", "Docker"]
        
        covered_lower = [s.lower() for s in covered]
        all_covered = all(
            any(exp.lower() in covered_lower or covered_lower.count(exp.lower()) > 0 
                for exp in expected_covered)
            for exp in expected_covered
        )
        
        if all_covered:
            print("  ✅ All expected skills are covered (normalization working correctly)")
        else:
            print("  ⚠️ Some expected skills are missing - check normalization")
        
        print("\n✅ Sanity check complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Sanity check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--sanity-check":
        sanity_check_normalization()
    else:
        main()
