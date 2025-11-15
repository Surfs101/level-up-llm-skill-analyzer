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
from pathlib import Path
from collections import defaultdict

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]
TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]

# Importance weights per bucket (higher → more important for gap closure)
BUCKET_WEIGHTS = {
    "ToolsPlatforms": 1.0,
    "FrameworksLibraries": 0.9,
    "ProgrammingLanguages": 0.8,
    "SoftSkills": 0.3,
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

def norm_skill(s: str) -> str:
    return (s or "").strip().lower()

def to_set_safe(d: dict, bucket: str):
    if not isinstance(d, dict):
        return set()
    v = d.get(bucket, [])
    if not isinstance(v, list):
        return set()
    return set(norm_skill(x) for x in v if isinstance(x, str) and x.strip())

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

def rank_missing_skills_by_priority(missing_skills_list: list, gaps_by_bucket: dict) -> list:
    """Rank missing skills by bucket importance (priority) instead of alphabetically.
    
    Args:
        missing_skills_list: List of missing skills (original case)
        gaps_by_bucket: Dict mapping bucket names to lists of missing skills in that bucket
    
    Returns:
        List of skills sorted by priority (highest priority first)
    """
    if not missing_skills_list:
        return []
    
    # Build a map of skill -> bucket for quick lookup
    skill_to_bucket = {}
    for bucket in BUCKETS:
        bucket_skills = gaps_by_bucket.get(bucket, [])
        for skill in bucket_skills:
            skill_lower = norm_skill(skill)
            skill_to_bucket[skill_lower] = bucket
    
    # Score each skill by bucket weight
    scored = []
    for skill in missing_skills_list:
        skill_lower = norm_skill(skill)
        bucket = skill_to_bucket.get(skill_lower, "SoftSkills")  # Default to SoftSkills if not found
        weight = BUCKET_WEIGHTS.get(bucket, 0.5)
        # Negative weight for descending sort (highest priority first)
        # Use skill.lower() as tiebreaker for consistent ordering
        scored.append((-(weight), skill.lower(), skill))
    
    # Sort by priority (highest weight first), then alphabetically as tiebreaker
    scored.sort()
    return [orig for _, __, orig in scored]

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
def score_match(resume_json: dict, job_json: dict, w_required: float, w_preferred: float):
    resume_sk = resume_json.get("skills", {}) or {}
    job_req_sk = (job_json.get("required", {}) or {}).get("skills", {}) or {}
    job_pref_sk = (job_json.get("preferred", {}) or {}).get("skills", {}) or {}

    # For pretty outputs, gather all original skills to map back case
    orig_map = build_original_case_map(
        *[resume_sk.get(b, []) for b in BUCKETS],
        *[job_req_sk.get(b, []) for b in BUCKETS],
        *[job_pref_sk.get(b, []) for b in BUCKETS],
    )

    per_bucket = {}
    # For overall Jaccard
    resume_all = set()
    job_all = set()

    total_req_needed = 0
    total_req_covered = 0
    total_pref_needed = 0
    total_pref_covered = 0

    # For bucket-agnostic overall coverage (prevents mis-bucketing mismatches)
    job_req_all = set()
    job_pref_all = set()

    for b in BUCKETS:
        have = to_set_safe(resume_sk, b)
        need_req = to_set_safe(job_req_sk, b)
        need_pref = to_set_safe(job_pref_sk, b)

        resume_all |= have
        job_all |= (need_req | need_pref)
        job_req_all |= need_req
        job_pref_all |= need_pref

        covered_req = sorted(list(have & need_req))
        missing_req_raw = list(need_req - have)

        covered_pref = sorted(list(have & need_pref))
        missing_pref_raw = list(need_pref - have)
        
        # Rank missing skills by priority (will be sorted later in overall section)
        # For per-bucket, we'll still show them but they'll be sorted by priority in the overall list
        missing_req = [orig_map.get(s, s) for s in missing_req_raw]
        missing_pref = [orig_map.get(s, s) for s in missing_pref_raw]

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
                "missing_skills": [orig_map.get(s, s) for s in missing_req],
            },
            "preferred": {
                "total": len(need_pref),
                "covered": len(covered_pref),
                "coverage_pct": pct(len(covered_pref), len(need_pref)),
                "covered_skills": [orig_map.get(s, s) for s in covered_pref],
                "missing_skills": [orig_map.get(s, s) for s in missing_pref],
            }
        }

    # Overall coverages
    # Bucket-agnostic: use unions so a resume skill counts even if bucketed differently
    req_cov_bucket_agnostic = len(resume_all & job_req_all)
    pref_cov_bucket_agnostic = len(resume_all & job_pref_all)
    req_total_bucket_agnostic = len(job_req_all)
    pref_total_bucket_agnostic = len(job_pref_all)
    req_cov_pct = pct(req_cov_bucket_agnostic, req_total_bucket_agnostic)
    pref_cov_pct = pct(pref_cov_bucket_agnostic, pref_total_bucket_agnostic)

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
    # J(A,B) = |A ∩ B| / |A ∪ B|
    inter = len(resume_all & job_all)
    uni = len(resume_all | job_all)
    jaccard_pct = pct(inter, uni)

    # Collect covered/missing lists overall in a bucket-agnostic way (pretty cased)
    covered_required_all = [orig_map.get(s, s) for s in sorted(list(resume_all & job_req_all))]
    missing_required_all_raw = [orig_map.get(s, s) for s in list(job_req_all - resume_all)]
    covered_preferred_all = [orig_map.get(s, s) for s in sorted(list(resume_all & job_pref_all))]
    missing_preferred_all_raw = [orig_map.get(s, s) for s in list(job_pref_all - resume_all)]
    
    # Build gaps by bucket for priority ranking
    gaps_required_by_bucket = {}
    gaps_preferred_by_bucket = {}
    for b in BUCKETS:
        have = to_set_safe(resume_sk, b)
        need_req = to_set_safe(job_req_sk, b)
        need_pref = to_set_safe(job_pref_sk, b)
        gaps_required_by_bucket[b] = [orig_map.get(s, s) for s in (need_req - have)]
        gaps_preferred_by_bucket[b] = [orig_map.get(s, s) for s in (need_pref - have)]
    
    # Rank missing skills by priority instead of alphabetically
    missing_required_all = rank_missing_skills_by_priority(missing_required_all_raw, gaps_required_by_bucket)
    missing_preferred_all = rank_missing_skills_by_priority(missing_preferred_all_raw, gaps_preferred_by_bucket)

    # Extra skills on resume not mentioned in job (could be nice-to-have)
    extra_resume = sorted(list(resume_all - job_all))
    extra_resume = [orig_map.get(s, s) for s in extra_resume]

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

    return {
        "summary": summary,
        "by_bucket": per_bucket,
        "covered_skills": {
            "required": sorted(list(set(covered_required_all))),
            "preferred": sorted(list(set(covered_preferred_all)))
        },
        "missing_skills": {
            "required": list(dict.fromkeys(missing_required_all)),  # Preserve priority order, remove duplicates
            "preferred": list(dict.fromkeys(missing_preferred_all))  # Preserve priority order, remove duplicates
        },
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

    data = score_match(resume_json, job_json, w_req, w_pref)
    write_outputs(data, Path(args.outdir), args.label)

if __name__ == "__main__":
    main()
