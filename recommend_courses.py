# recommend_courses.py
# Course recommendations query MongoDB using course datasets
# Accepts a list of skills, compares them to course titles, and returns top matches

import os
import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from collections import defaultdict

BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms", "SoftSkills"]
PLATFORM_WHITELIST = {"DeepLearning.AI", "Udemy", "Coursera"}
# Course recommendations should ignore soft skills entirely
TARGET_BUCKETS = ["ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"]
# Importance weights per bucket (higher → more important for gap closure)
BUCKET_WEIGHTS = {
    "ToolsPlatforms": 1.0,
    "FrameworksLibraries": 0.9,
    "ProgrammingLanguages": 0.8,
    "SoftSkills": 0.3,
}

# MongoDB connection settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "courses_db"
UDEMY_COLLECTION = "udemy_courses"
COURSERA_COLLECTION = "coursera_courses"


# ---------- MongoDB Connection ----------
def get_mongo_client():
    """Get MongoDB client connection."""
    return MongoClient(MONGODB_URI)


def get_db():
    """Get courses database."""
    client = get_mongo_client()
    return client[DB_NAME]


# ---------- utils ----------
def load_json(p: str):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_resume_skills(resume_json: dict):
    skills = resume_json.get("skills", {})
    return {b: set(skills.get(b, [])) for b in TARGET_BUCKETS}


def get_job_required_skills(job_json: dict):
    required = job_json.get("required", {}).get("skills", {})
    return {b: set(required.get(b, [])) for b in TARGET_BUCKETS}


def get_job_preferred_skills(job_json: dict):
    preferred = job_json.get("preferred", {}).get("skills", {})
    return {b: set(preferred.get(b, [])) for b in TARGET_BUCKETS}


def compute_gaps(have: dict, need: dict):
    return {b: sorted(list(need[b] - have[b])) for b in TARGET_BUCKETS}


def _rank_missing_skills(gaps: dict) -> list:
    """Rank missing skills by bucket importance and alphabetical as tiebreaker."""
    scored = []
    for b in TARGET_BUCKETS:
        for s in gaps.get(b, []) or []:
            scored.append((-(BUCKET_WEIGHTS.get(b, 0.5)), s.lower(), s))
    scored.sort()
    return [orig for _, __, orig in scored]


def gaps_empty(gaps: dict):
    return all(len(v) == 0 for v in gaps.values())


def normalize_price(price_value) -> str:
    """Normalize price to string format."""
    if price_value is None or price_value == "":
        return "Free"
    if isinstance(price_value, (int, float)):
        if price_value == 0:
            return "Free"
        return f"${price_value:.2f}"
    if isinstance(price_value, str):
        price_str = price_value.strip()
        if not price_str or price_str.lower() in ["free", "0", "0.0"]:
            return "Free"
        # Try to parse as number
        try:
            num_price = float(price_str.replace("$", "").replace(",", ""))
            if num_price == 0:
                return "Free"
            return f"${num_price:.2f}"
        except:
            return price_str
    return "Free"


def normalize_rating(rating_value) -> Optional[float]:
    """Normalize rating to float."""
    if rating_value is None:
        return None
    try:
        return float(rating_value)
    except (ValueError, TypeError):
        return None


def normalize_duration(duration_value, platform: str) -> str:
    """Normalize duration to string format."""
    if duration_value is None:
        return "N/A"
    if isinstance(duration_value, (int, float)):
        if platform == "Udemy":
            return f"{duration_value} hours"
        else:
            return f"{duration_value} weeks"
    if isinstance(duration_value, str):
        return duration_value
    return "N/A"


def normalize_level(level_value) -> str:
    """Normalize level to Beginner/Intermediate/Advanced."""
    if level_value is None:
        return "All Levels"
    level_str = str(level_value).strip()
    level_lower = level_str.lower()
    if "beginner" in level_lower or "all" in level_lower:
        return "Beginner"
    if "intermediate" in level_lower:
        return "Intermediate"
    if "advanced" in level_lower:
        return "Advanced"
    return level_str


def skill_match_score(skill: str, title: str) -> float:
    """
    Calculate match score between a skill and a course title.
    Returns a score between 0 and 1.
    """
    if not skill or not title:
        return 0.0
    
    skill_lower = skill.lower().strip()
    title_lower = title.lower().strip()
    
    # Exact match
    if skill_lower == title_lower:
        return 1.0
    
    # Skill is a word in the title (word boundary match)
    if re.search(r'\b' + re.escape(skill_lower) + r'\b', title_lower):
        return 0.9
    
    # Skill is a substring of the title
    if skill_lower in title_lower:
        return 0.7
    
    # Title contains skill words (for multi-word skills)
    skill_words = skill_lower.split()
    if len(skill_words) > 1:
        matches = sum(1 for word in skill_words if word in title_lower)
        if matches == len(skill_words):
            return 0.8
        if matches > 0:
            return 0.5 * (matches / len(skill_words))
    
    return 0.0


def match_courses_to_skills(skills: List[str], courses: List[Dict], top_n: int = 10) -> List[Dict]:
    """
    Match courses to skills and return top N matches sorted by relevance.
    
    Args:
        skills: List of skills to match against
        courses: List of course documents from MongoDB
        top_n: Number of top matches to return
    
    Returns:
        List of course dictionaries with match scores and matched skills
    """
    scored_courses = []
    
    for course in courses:
        title = course.get("course_title") or course.get("title") or course.get("name") or ""
        if not title:
            continue
        
        # Calculate match scores for each skill
        matched_skills = []
        total_score = 0.0
        
        for skill in skills:
            score = skill_match_score(skill, title)
            if score > 0:
                matched_skills.append(skill)
                total_score += score
        
        if matched_skills:
            # Average score multiplied by number of matched skills (boost for multi-skill coverage)
            avg_score = total_score / len(skills) if skills else 0
            coverage_boost = len(matched_skills) / max(1, len(skills))
            final_score = avg_score * (1 + 0.5 * coverage_boost)
            
            course_copy = dict(course)
            course_copy["_match_score"] = final_score
            course_copy["_matched_skills"] = matched_skills
            scored_courses.append(course_copy)
    
    # Sort by score descending, then by rating descending
    scored_courses.sort(key=lambda x: (
        -x.get("_match_score", 0),
        -(normalize_rating(x.get("Rating") or x.get("rating")) or 0)
    ))
    
    return scored_courses[:top_n]


def fetch_courses_from_mongo(skills: List[str], max_results: int = 100) -> Dict[str, List[Dict]]:
    """
    Fetch courses from MongoDB matching the given skills.
    
    Args:
        skills: List of skills to match against
        max_results: Maximum number of results to fetch per platform
    
    Returns:
        Dictionary with 'udemy' and 'coursera' keys containing course lists
    """
    db = get_db()
    results = {"udemy": [], "coursera": []}
    
    # Build search query - search for courses whose titles contain any of the skills
    skill_patterns = [re.compile(re.escape(skill.lower()), re.IGNORECASE) for skill in skills]
    
    # Query Udemy courses
    try:
        udemy_courses = list(db[UDEMY_COLLECTION].find(
            {"course_title": {"$exists": True, "$ne": None}},
            limit=max_results * 2  # Fetch more to filter later
        ))
        # Match and score courses
        udemy_matched = match_courses_to_skills(skills, udemy_courses, top_n=max_results)
        results["udemy"] = udemy_matched
    except Exception as e:
        print(f"Warning: Error fetching Udemy courses: {e}")
        results["udemy"] = []
    
    # Query Coursera courses
    # Coursera CSV might have different structure - try multiple field names
    # If it's a reviews file, we might need to group by course name/title
    try:
        coursera_query = {
            "$or": [
                {"course_title": {"$exists": True, "$ne": None, "$ne": ""}},
                {"title": {"$exists": True, "$ne": None, "$ne": ""}},
                {"name": {"$exists": True, "$ne": None, "$ne": ""}},
                {"Course Name": {"$exists": True, "$ne": None, "$ne": ""}},
            ]
        }
        coursera_courses_raw = list(db[COURSERA_COLLECTION].find(
            coursera_query,
            limit=max_results * 3  # Fetch more to filter later (reviews file might have duplicates)
        ))
        
        # If it's a reviews file, we need to deduplicate by course name
        # Group by title/name and take the first occurrence with best rating
        course_dict = {}
        for course in coursera_courses_raw:
            title = (course.get("course_title") or course.get("title") or 
                    course.get("name") or course.get("Course Name") or "").strip()
            if not title:
                continue
            
            # Use title as key for deduplication
            if title not in course_dict:
                course_dict[title] = course
            else:
                # If duplicate, keep the one with higher rating
                existing_rating = normalize_rating(
                    course_dict[title].get("Rating") or course_dict[title].get("rating")
                ) or 0
                new_rating = normalize_rating(
                    course.get("Rating") or course.get("rating")
                ) or 0
                if new_rating > existing_rating:
                    course_dict[title] = course
        
        coursera_courses = list(course_dict.values())
        
        # Match and score courses
        coursera_matched = match_courses_to_skills(skills, coursera_courses, top_n=max_results)
        results["coursera"] = coursera_matched
    except Exception as e:
        print(f"Warning: Error fetching Coursera courses: {e}")
        results["coursera"] = []
    
    return results


def format_course_for_output(course: Dict, platform: str) -> Dict:
    """
    Format a MongoDB course document to the expected output format.
    
    Args:
        course: Course document from MongoDB
        platform: Platform name (e.g., "Udemy", "Coursera")
    
    Returns:
        Formatted course dictionary
    """
    # Extract title from various possible field names
    title = (course.get("course_title") or course.get("title") or 
             course.get("name") or course.get("Course Name") or "").strip()
    
    # Extract URL from various possible field names
    url = (course.get("url") or course.get("link") or 
           course.get("course_url") or course.get("Course URL") or None)
    
    # Extract price and determine if free/paid
    # Try multiple field names for price
    price_raw = (course.get("price") or course.get("cost") or 
                 course.get("Price") or course.get("Cost") or 0)
    price = normalize_price(price_raw)
    is_free = price.lower() == "free"
    
    # Extract rating from various possible field names
    rating = normalize_rating(
        course.get("Rating") or course.get("rating") or 
        course.get("course_rating") or course.get("average_rating")
    )
    
    # Extract duration from various possible field names
    duration_raw = (course.get("content_duration") or course.get("duration") or
                   course.get("Duration") or course.get("Content Duration"))
    duration = normalize_duration(duration_raw, platform)
    
    # Extract level/difficulty from various possible field names
    level = normalize_level(
        course.get("level") or course.get("difficulty") or 
        course.get("Level") or course.get("Difficulty")
    )
    
    # Get matched skills
    matched_skills = course.get("_matched_skills", [])
    
    # Extract description if available
    description = (course.get("description") or course.get("Description") or
                  course.get("course_description") or 
                  f"Course covering {', '.join(matched_skills) if matched_skills else 'relevant skills'}")
    
    # Format output
    formatted = {
        "title": title,
        "platform": platform,
        "skills_covered": matched_skills,
        "additional_skills": [],  # Could be enhanced to extract from course description
        "duration": duration,
        "difficulty": level,
        "description": description,
        "why_efficient": f"Covers multiple skills: {', '.join(matched_skills)}" if matched_skills else "Covers relevant skills",
        "cost": price,
        "link": url,
        "rating": rating  # Added rating as requested
    }
    
    return formatted


def get_course_recommendations(
    skills: List[str],
    require_free: bool = False,
    require_paid: bool = False,
    max_free: int = 5,
    max_paid: int = 5
) -> Dict[str, Any]:
    """
    Get course recommendations from MongoDB based on skills.
    
    Args:
        skills: List of skills to match against
        require_free: If True, only return free courses
        require_paid: If True, only return paid courses
        max_free: Maximum number of free courses to return
        max_paid: Maximum number of paid courses to return
    
    Returns:
        Dictionary with course recommendations in expected format
    """
    if not skills:
        return {
            "free_courses": [],
            "paid_courses": [],
            "skill_coverage": {},
            "uncovered_skills": skills,
            "coverage_percentage": 0
        }
    
    # Fetch courses from MongoDB
    all_courses = fetch_courses_from_mongo(skills, max_results=max(max_free, max_paid) * 2)
    
    # Separate free and paid courses
    free_courses = []
    paid_courses = []
    
    # Process Udemy courses
    for course in all_courses["udemy"]:
        price_raw = course.get("price") or course.get("cost") or 0
        price = normalize_price(price_raw)
        is_free = price.lower() == "free"
        
        formatted = format_course_for_output(course, "Udemy")
        
        if is_free and not require_paid:
            free_courses.append(formatted)
        elif not is_free and not require_free:
            paid_courses.append(formatted)
    
    # Process Coursera courses
    for course in all_courses["coursera"]:
        price_raw = course.get("price") or course.get("cost") or 0
        price = normalize_price(price_raw)
        is_free = price.lower() == "free"
        
        formatted = format_course_for_output(course, "Coursera")
        
        if is_free and not require_paid:
            free_courses.append(formatted)
        elif not is_free and not require_free:
            paid_courses.append(formatted)
    
    # Sort by match score (if available) and rating
    def sort_key(c):
        match_score = c.get("_match_score", 0)
        rating = c.get("rating") or 0
        return (-match_score, -rating)
    
    free_courses.sort(key=sort_key)
    paid_courses.sort(key=sort_key)
    
    # Limit results
    free_courses = free_courses[:max_free]
    paid_courses = paid_courses[:max_paid]
    
    # Remove internal fields
    for course in free_courses + paid_courses:
        course.pop("_match_score", None)
        course.pop("_matched_skills", None)
    
    # Compute skill coverage
    skill_coverage = defaultdict(list)
    uncovered = set(skills)
    
    for course in free_courses + paid_courses:
        title = course.get("title", "")
        for skill in course.get("skills_covered", []):
            if skill in skills:
                if title not in skill_coverage[skill]:
                    skill_coverage[skill].append(title)
                uncovered.discard(skill)
    
    uncovered_skills = sorted(list(uncovered))
    coverage_percentage = round(100 * (len(skills) - len(uncovered_skills)) / max(1, len(skills)))
    
    return {
        "free_courses": free_courses,
        "paid_courses": paid_courses,
        "skill_coverage": dict(skill_coverage),
        "uncovered_skills": uncovered_skills,
        "coverage_percentage": coverage_percentage
    }


def compute_coverage(target_set, free_courses, paid_courses):
    coverage = {s: [] for s in target_set}
    def add_course(course):
        title = (course.get("title") or "").strip()
        for s in course.get("skills_covered", []):
            if s in coverage and title and title not in coverage[s]:
                coverage[s].append(title)
    for c in free_courses: add_course(c)
    for c in paid_courses: add_course(c)
    covered = {s for s, lst in coverage.items() if lst}
    uncovered = sorted(list(set(target_set) - covered))
    pct = round(100 * len(covered) / max(1, len(target_set)))
    return coverage, uncovered, pct


# ---------- main recommendation function ----------
def recommend_courses_from_gaps(
    resume_json: dict,
    job_json: dict,
    role: str = "Target Role",
    require_free: bool = False,
    require_paid: bool = False,
    max_free: int = 1,
    max_paid: int = 1
) -> dict:
    """
    Main function to get course recommendations based on skill gaps.
    This is the primary entry point for the FastAPI app.
    
    Args:
        resume_json: Resume skills JSON
        job_json: Job skills JSON
        role: Target role name
        require_free: If True, only return free courses
        require_paid: If True, only return paid courses
        max_free: Maximum free courses to return (default 1 for compatibility)
        max_paid: Maximum paid courses to return (default 1 for compatibility)
    
    Returns:
        Dictionary with course recommendations
    """
    have = get_resume_skills(resume_json)
    need_required = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need_required)
    
    # If no REQUIRED gaps, fall back to PREFERRED gaps
    if gaps_empty(gaps):
        need_pref = get_job_preferred_skills(job_json)
        gaps = compute_gaps(have, need_pref)
    
    # Flatten gaps to a list of skills
    target_skills = sorted({s for b in TARGET_BUCKETS for s in gaps.get(b, [])})
    
    if not target_skills:
        return {
            "free_courses": [],
            "paid_courses": [],
            "skill_coverage": {},
            "uncovered_skills": [],
            "coverage_percentage": 100
        }
    
    # Get recommendations from MongoDB
    recommendations = get_course_recommendations(
        skills=target_skills,
        require_free=require_free,
        require_paid=require_paid,
        max_free=max_free,
        max_paid=max_paid
    )
    
    return recommendations


# ---------- output functions (kept for compatibility) ----------
def dict_to_md_table(d: dict):
    if not d:
        return "_None_"
    lines = ["| Key | Value |", "|---|---|"]
    for k, v in d.items():
        if isinstance(v, list):
            v_str = ", ".join(v) if v else "-"
        elif isinstance(v, dict):
            inner = ", ".join(f"{ik}:{len(iv) if isinstance(iv, list) else str(iv)}" for ik, iv in v.items())
            v_str = inner or "-"
        else:
            v_str = str(v)
        lines.append(f"| {k} | {v_str} |")
    return "\n".join(lines)


def write_outputs(role: str, gaps: dict, data: dict, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    role_slug = role.lower().replace(" ", "_")
    json_path = outdir / f"recommendations_{role_slug}.json"
    md_path = outdir / f"recommendations_{role_slug}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    md = []
    md.append(f"# {role} – Course Recommendations (1 Free, 1 Paid)\n")
    md.append("## Required Skill Gaps (by bucket)\n")
    md.append(dict_to_md_table(gaps))

    md.append("\n\n## Free Course\n")
    if data.get("free_courses"):
        c = data["free_courses"][0]
        md.extend([
            f"- **Title:** {c['title']}",
            f"- **Platform:** {c['platform']}",
            f"- **Rating:** {c.get('rating', 'N/A')}",
            f"- **Skills Covered:** {', '.join(c.get('skills_covered', [])) or '-'}",
            f"- **Additional Skills:** {', '.join(c.get('additional_skills', [])) or '-'}",
            f"- **Duration:** {c['duration']}",
            f"- **Difficulty:** {c['difficulty']}",
            f"- **Cost:** {c['cost']}",
            f"- **Link:** {c['link'] or '—'}",
            f"- **Why Efficient:** {c['why_efficient']}",
            f"{c['description']}",
        ])
    else:
        md.append("_None_")

    md.append("\n\n## Paid Course\n")
    if data.get("paid_courses"):
        c = data["paid_courses"][0]
        md.extend([
            f"- **Title:** {c['title']}",
            f"- **Platform:** {c['platform']}",
            f"- **Rating:** {c.get('rating', 'N/A')}",
            f"- **Skills Covered:** {', '.join(c.get('skills_covered', [])) or '-'}",
            f"- **Additional Skills:** {', '.join(c.get('additional_skills', [])) or '-'}",
            f"- **Duration:** {c['duration']}",
            f"- **Difficulty:** {c['difficulty']}",
            f"- **Cost:** {c['cost']}",
            f"- **Link:** {c['link'] or '—'}",
            f"- **Why Efficient:** {c['why_efficient']}",
            f"{c['description']}",
        ])
    else:
        md.append("_None_")

    md.append("\n\n## Skill Coverage Map\n")
    md.append(dict_to_md_table(data.get("skill_coverage", {})))

    md.append("\n\n## Uncovered Skills\n")
    if data.get("uncovered_skills"):
        md.append(", ".join(data["uncovered_skills"]))
    else:
        md.append("_All target skills covered_")

    md.append(f"\n\n## Coverage Percentage\n**{data.get('coverage_percentage', 0)}%**\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"✅ Saved JSON → {json_path}")
    print(f"✅ Saved Markdown → {md_path}")


# ---------- main ----------
def main():
    parser = argparse.ArgumentParser(description="Course recommender using MongoDB")
    parser.add_argument("--resume", required=True, help="Path to resume_*_skills.json")
    parser.add_argument("--job", required=True, help="Path to job_description_*_skills.json")
    parser.add_argument("--role", required=True, help='Target role (e.g., "MLOps Engineer")')
    parser.add_argument("--outdir", default="recommendations_out", help="Output directory")
    parser.add_argument("--max-free", type=int, default=5, help="Maximum free courses to return")
    parser.add_argument("--max-paid", type=int, default=5, help="Maximum paid courses to return")
    args = parser.parse_args()

    load_dotenv()

    resume_json = load_json(args.resume)
    job_json = load_json(args.job)

    # Get recommendations
    recommendations = recommend_courses_from_gaps(
        resume_json=resume_json,
        job_json=job_json,
        role=args.role,
        max_free=args.max_free,
        max_paid=args.max_paid
    )

    # Compute gaps for output
    have = get_resume_skills(resume_json)
    need = get_job_required_skills(job_json)
    gaps = compute_gaps(have, need)

    write_outputs(args.role, gaps, recommendations, Path(args.outdir))


if __name__ == "__main__":
    main()
