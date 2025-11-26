# recommend_courses.py
# Course recommendations query MongoDB using course datasetsv
# Accepts a list of skills, compares them to course titles, and returns top matches

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from collections import defaultdict
from openai import OpenAI

# Load environment variables
load_dotenv()

PLATFORM_WHITELIST = {"DeepLearning.AI", "Udemy", "Coursera"}

# MongoDB connection settings
# Support both old (MONGODB_URI) and new (MONGO_URI) environment variable names for compatibility
MONGODB_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
# Support both old (courses_db) and new (aijs_capstone) database names
# Default to "aijs_capstone" to match the loading script, but fallback to "courses_db" for backward compatibility
DB_NAME = os.getenv("MONGO_DB_NAME", "aijs_capstone")
# Separate collections for each course type
FREE_UDEMY_COLLECTION = "free_udemy_courses"
PAID_UDEMY_COLLECTION = "paid_udemy_courses"
FREE_COURSERA_COLLECTION = "free_coursera_courses"
PAID_COURSERA_COLLECTION = "paid_coursera_courses"


# ---------- MongoDB Connection ----------
def get_mongo_client():
    """Get MongoDB client connection."""
    return MongoClient(MONGODB_URI)


def get_db():
    """Get courses database."""
    client = get_mongo_client()
    return client[DB_NAME]


# ---------- utils ----------
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


def match_courses_with_llm(skills: List[str], courses: List[Dict], top_n: int = 10,
                           skill_weights: Optional[Dict[str, float]] = None,
                           critical_skills: Optional[List[str]] = None) -> List[Dict]:
    """
    Use LLM to intelligently match and rank courses based on skills.
    This replaces complex regex/scoring logic with semantic understanding.
    
    Args:
        skills: List of skills to match against
        courses: List of course documents from MongoDB
        top_n: Number of top matches to return
        skill_weights: Optional dict mapping skill names to importance weights
        critical_skills: Optional list of most critical skills (ordered by importance)
    
    Returns:
        List of course dictionaries with match scores and matched skills
    """
    if not skills or not courses:
        return []
    
    # Identify critical skills if not provided
    if critical_skills is None:
        if skill_weights:
            sorted_by_weight = sorted(skills, key=lambda s: skill_weights.get(s, 1.0), reverse=True)
            critical_skills = sorted_by_weight[:3] if len(sorted_by_weight) >= 3 else sorted_by_weight
        else:
            critical_skills = skills[:3] if len(skills) >= 3 else skills
    
    # Prepare course summaries for LLM (limit to avoid token limits)
    course_summaries = []
    for idx, course in enumerate(courses[:100]):  # Limit to 100 courses to avoid token limits
        title_raw = course.get("course_title") or course.get("title") or course.get("name") or ""
        title = str(title_raw).strip() if title_raw is not None else ""
        if not title or title.lower() == "nan":
            continue
        
        desc_raw = (course.get("description") or course.get("Description") or
                   course.get("course_description") or course.get("Course Description") or
                   course.get("content") or course.get("Content") or
                   course.get("summary") or course.get("Summary") or
                   course.get("overview") or course.get("Overview") or "")
        description = str(desc_raw).strip() if desc_raw is not None else ""
        # Limit description to 300 chars to save tokens
        description = description[:300] + "..." if len(description) > 300 else description
        
        rating = normalize_rating(course.get("Rating") or course.get("rating"))
        platform = course.get("_platform") or course.get("platform") or "Unknown"
        cost_type = course.get("_cost_type", "Paid")  # Get cost type from metadata
        
        course_summaries.append({
            "id": idx,
            "title": title,
            "description": description,
            "rating": rating,
            "platform": platform,
            "cost_type": cost_type,  # Include cost type for LLM
            "_original_course": course  # Keep reference to original
        })
    
    if not course_summaries:
        return []
    
    # Build LLM prompt
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    critical_skills_str = f"\nCRITICAL SKILLS (must prioritize these): {', '.join(critical_skills[:3])}" if critical_skills else ""
    skills_str = ', '.join(skills)
    
    prompt = f"""You are a course recommendation expert. Find the BEST courses for these required skills.

REQUIRED SKILLS: {skills_str}
{critical_skills_str}

COURSES TO EVALUATE:
{json.dumps([{k: v for k, v in c.items() if k not in ["_original_course", "_platform", "_cost_type"]} for c in course_summaries], indent=2)}

Task:
1. For each course, determine which skills it covers (can be implicit - e.g., "Web Development" covers HTML, CSS, JavaScript)
2. Prioritize courses that:
   - Cover the MOST missing skills in one course (efficiency)
   - Focus on the most CRITICAL skills (already ranked - top skills are most important)
   - Have high quality (ratings, platform reputation)
3. Rank courses by overall value considering:
   - **Skill Coverage**: How many missing skills does it cover? (prioritize courses covering multiple skills)
   - **Critical Skills Focus**: Does it cover the top-ranked critical skills?
   - **Quality**: Course ratings, platform reputation (Udemy/Coursera are reputable)
   - **Comprehensiveness**: Covers multiple skills efficiently
   - **Value**: Free courses preferred when quality is similar
4. Return top {top_n} BEST courses ranked by overall quality and relevance

Return JSON in this format:
{{
  "ranked_courses": [
    {{
      "id": 0,
      "matched_skills": ["HTML", "CSS", "JavaScript"],
      "relevance_score": 0.95,
      "quality_score": 0.9,
      "reason": "Comprehensive web development course covering all required frontend skills with high ratings"
    }},
    ...
  ]
}}

Make sure to:
- Match skills semantically (e.g., "Full Stack Development" = HTML + CSS + JavaScript + backend)
- Prioritize courses that cover critical skills
- Consider course quality (ratings, platform)
- Return exactly {top_n} courses (or fewer if not enough good matches)"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.1",  # Use GPT-5.1 for better course selection
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for consistent results
        )
        
        result = json.loads(response.choices[0].message.content)
        ranked = result.get("ranked_courses", [])
        
        # Map back to original course objects
        matched_courses = []
        for ranked_item in ranked:
            course_id = ranked_item.get("id")
            if course_id < len(course_summaries):
                original_course = course_summaries[course_id]["_original_course"]
                course = dict(original_course)
                course["_matched_skills"] = ranked_item.get("matched_skills", [])
                course["_relevance_score"] = ranked_item.get("relevance_score", 0)
                course["_quality_score"] = ranked_item.get("quality_score", 0)
                course["_match_reason"] = ranked_item.get("reason", "")
                # Calculate overall match score for sorting
                course["_match_score"] = (ranked_item.get("relevance_score", 0) * 0.7 + 
                                         ranked_item.get("quality_score", 0) * 0.3)
                matched_courses.append(course)
        
        # Sort by match score (already ranked by LLM, but ensure consistency)
        matched_courses.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
        
        return matched_courses[:top_n]
        
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            print(f"Error: OpenAI API quota exceeded. Please check your billing and plan.")
            raise Exception(f"OpenAI API quota exceeded. Please check your billing and plan. Error: {error_msg}")
        else:
            print(f"Warning: LLM matching failed: {e}. Falling back to simple matching.")
            import traceback
            traceback.print_exc()
            # Fallback: return courses with basic title matching
            return courses[:top_n]


def fetch_all_courses_from_mongo(skills: List[str], min_courses: int = 50) -> List[Dict]:
    """
    Fetch ALL courses (free + paid, Udemy + Coursera) from MongoDB.
    Returns raw course documents without LLM matching.
    
    Args:
        skills: List of skills to search for
        min_courses: Minimum number of courses to fetch (at least 50)
    
    Returns:
        List of course documents with platform and cost info added
    """
    db = get_db()
    all_courses = []
    
    if not skills:
        return all_courses
    
    # Build search query for skills (search in title and description)
    skill_keywords = [skill.lower() for skill in skills[:10]]  # Limit to top 10 skills
    search_query = {
        "$or": [
            {"course_title": {"$regex": "|".join(skill_keywords), "$options": "i"}},
            {"title": {"$regex": "|".join(skill_keywords), "$options": "i"}},
            {"description": {"$regex": "|".join(skill_keywords), "$options": "i"}},
            {"Description": {"$regex": "|".join(skill_keywords), "$options": "i"}},
        ]
    }
    
    courses_per_collection = max(15, min_courses // 4)  # Distribute across 4 collections
    
    # Fetch from all collections
    collections = [
        (FREE_UDEMY_COLLECTION, "Udemy", "Free"),
        (PAID_UDEMY_COLLECTION, "Udemy", "Paid"),
        (FREE_COURSERA_COLLECTION, "Coursera", "Free"),
        (PAID_COURSERA_COLLECTION, "Coursera", "Paid"),
    ]
    
    for collection_name, platform, cost_type in collections:
        try:
            # Fetch courses related to skills
            courses = list(db[collection_name].find(search_query).sort("rating", -1).limit(courses_per_collection))
            
            # If not enough, fetch more general courses
            if len(courses) < courses_per_collection:
                additional = list(db[collection_name].find({}).sort("rating", -1).limit(courses_per_collection - len(courses)))
                courses.extend(additional)
            
            # Add platform and cost metadata
            for course in courses:
                course["_platform"] = platform
                course["_cost_type"] = cost_type
            
            all_courses.extend(courses)
            print(f"Debug: Fetched {len(courses)} {cost_type} {platform} courses")
        except Exception as e:
            print(f"Warning: Error fetching from {collection_name}: {e}")
            continue
    
    # Deduplicate Coursera courses by title (Udemy usually doesn't have duplicates)
    course_dict = {}
    for course in all_courses:
        title_raw = (course.get("course_title") or course.get("title") or 
                    course.get("name") or course.get("Course Name") or "")
        title = str(title_raw).strip() if title_raw is not None else ""
        if not title or title.lower() == "nan":
            continue
        
        # For Coursera, deduplicate; for Udemy, keep all
        if course["_platform"] == "Coursera":
            if title not in course_dict:
                course_dict[title] = course
            else:
                # Keep the one with higher rating
                existing_rating = normalize_rating(course_dict[title].get("Rating") or course_dict[title].get("rating")) or 0
                new_rating = normalize_rating(course.get("Rating") or course.get("rating")) or 0
                if new_rating > existing_rating:
                    course_dict[title] = course
        else:
            # For Udemy, add directly (no deduplication needed)
            if title not in course_dict:
                course_dict[title] = course
    
    deduplicated = list(course_dict.values())
    print(f"Debug: Fetched {len(deduplicated)} total courses (deduplicated)")
    
    return deduplicated


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
    # Safely convert to string to handle float/None values
    title_raw = (course.get("course_title") or course.get("title") or 
                 course.get("name") or course.get("Course Name") or "")
    title = str(title_raw).strip() if title_raw is not None else ""
    
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
    
    # Get matched skills (from LLM matching)
    matched_skills = course.get("_matched_skills", [])
    
    # Extract description if available
    # Safely convert to string to handle float/None values
    desc_raw = (course.get("description") or course.get("Description") or
                course.get("course_description") or "")
    description = str(desc_raw).strip() if desc_raw is not None else ""
    if not description:
        description = f"Course covering {', '.join(matched_skills) if matched_skills else 'relevant skills'}"
    
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
    max_paid: int = 5,
    skill_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Get course recommendations from MongoDB based on skills.
    Fetches ALL courses first, then uses LLM to select best free and paid courses.
    
    Args:
        skills: List of skills to match against
        require_free: If True, only return free courses
        require_paid: If True, only return paid courses
        max_free: Maximum number of free courses to return
        max_paid: Maximum number of paid courses to return
        skill_weights: Optional dict mapping skill names to importance weights
    
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
    
    # Step 1: Fetch ALL courses at once (free + paid, Udemy + Coursera)
    min_courses = max(50, (max_free + max_paid) * 3)  # At least 50, or 3x what we need
    all_courses_raw = fetch_all_courses_from_mongo(skills, min_courses=min_courses)
    
    if not all_courses_raw:
        return {
            "free_courses": [],
            "paid_courses": [],
            "skill_coverage": {},
            "uncovered_skills": skills,
            "coverage_percentage": 0
        }
    
    # Step 2: Use LLM to select best courses from ALL fetched courses
    # Use first 3 skills from the list (which is already priority-ordered if ranked_skills was passed)
    critical_skills = skills[:3] if len(skills) >= 3 else skills
    
    try:
        # LLM selects best courses from all platforms and cost types
        # Skills list is already in priority order (most critical first)
        matched_courses = match_courses_with_llm(
            skills, 
            all_courses_raw, 
            top_n=max_free + max_paid + 5,  # Get a few extra for filtering
            skill_weights=skill_weights, 
            critical_skills=critical_skills  # Top 3 are the most critical (priority-ordered)
        )
        print(f"Debug: LLM matched {len(matched_courses)} courses from all platforms")
    except Exception as e:
        print(f"Warning: LLM matching failed: {e}. Using simple fallback.")
        import traceback
        traceback.print_exc()
        # Fallback: return first courses
        matched_courses = all_courses_raw[:max_free + max_paid]
    
    # Step 3: Separate into free and paid, format for output
    free_courses = []
    paid_courses = []
    
    for course in matched_courses:
        cost_type = course.get("_cost_type", "Paid")
        platform = course.get("_platform", "Unknown")
        
        # Skip if restricted
        if require_free and cost_type != "Free":
            continue
        if require_paid and cost_type != "Paid":
            continue
        
        formatted = format_course_for_output(course, platform)
        formatted["cost"] = "Free" if cost_type == "Free" else "Paid"
        
        if cost_type == "Free" and len(free_courses) < max_free:
            free_courses.append(formatted)
        elif cost_type == "Paid" and len(paid_courses) < max_paid:
            paid_courses.append(formatted)
        
        # Stop if we have enough
        if len(free_courses) >= max_free and len(paid_courses) >= max_paid:
            break
    
    # Sort by match score (if available) and rating
    def sort_key(c):
        # Try to get match score from internal fields first
        match_score = c.get("_match_score", 0)
        # If not available, try to calculate from skills_covered
        if match_score == 0 and c.get("skills_covered"):
            match_score = len(c.get("skills_covered", [])) / max(1, len(skills)) if skills else 0
        rating = c.get("rating") or 0
        return (-match_score, -rating)
    
    free_courses.sort(key=sort_key)
    paid_courses.sort(key=sort_key)
    
    # Ensure we have at least one free and one paid if available and not restricted
    # If we have free courses but need more, try to get from the other list
    if not require_free and not require_paid:
        # If we have free but need paid, try to find paid courses
        if len(free_courses) > 0 and len(paid_courses) == 0 and max_paid > 0:
            # Try to fetch more courses specifically for paid
            print("Debug: Found free courses but no paid courses, fetching more...")
            # Already fetched enough above, this is just for logging
        # If we have paid but need free, try to find free courses  
        if len(paid_courses) > 0 and len(free_courses) == 0 and max_free > 0:
            print("Debug: Found paid courses but no free courses, fetching more...")
            # Already fetched enough above, this is just for logging
    
    # Limit results
    free_courses = free_courses[:max_free]
    paid_courses = paid_courses[:max_paid]
    
    print(f"Debug: Returning {len(free_courses)} free and {len(paid_courses)} paid courses")
    
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


# ---------- main recommendation function ----------
def recommend_courses_from_gaps(
    missing_skills_data: dict,
    role: str = "Target Role",
    require_free: bool = False,
    require_paid: bool = False,
    max_free: int = 1,
    max_paid: int = 1,
    ranked_skills: Optional[List[str]] = None
) -> dict:
    """
    Main function to get course recommendations based on **skill gaps** and pre-calculated weights
    from score_skills_match.
    
    This function simply uses the prioritized skills and weights already calculated by score_skills_match
    to fetch and match courses from MongoDB.
    
    Args:
        missing_skills_data: Dictionary containing:
            - "gaps": {"required": [skills], "preferred": [skills]}  # Flat lists, no buckets
            - "skill_weights": {"required": {skill: final_weight}, "preferred": {skill: final_weight}}
        role: Target role name (currently informational only)
        require_free: If True, only return free courses
        require_paid: If True, only return paid courses
        max_free: Maximum free courses to return (default 1 for compatibility)
        max_paid: Maximum paid courses to return (default 1 for compatibility)
        ranked_skills: Optional priority-ranked list of missing skills (from match_scores). 
                      If provided, this will be used instead of gaps, preserving priority order.
    
    Returns:
        Dictionary with course recommendations
    """
    gaps = missing_skills_data.get("gaps", {})
    skill_weights_dict = missing_skills_data.get("skill_weights", {})
    
    # Use required gaps first, fall back to preferred if no required gaps
    gaps_to_use = gaps.get("required", [])
    skill_weights_to_use = skill_weights_dict.get("required", {})
    
    if not gaps_to_use:  # Check if any required gaps exist
        gaps_to_use = gaps.get("preferred", [])
        skill_weights_to_use = skill_weights_dict.get("preferred", {})
    
    # Use priority-ranked skills if provided, otherwise use gaps directly (already flat lists)
    if ranked_skills:
        # Use the priority-ordered skills directly (preserves LLM ranking)
        target_skills = ranked_skills
    else:
        # Fallback: Use gaps directly (already a flat list)
        target_skills = gaps_to_use if isinstance(gaps_to_use, list) else []
    
    # If no skills, return empty (no gaps to close)
    if not target_skills:
        return {
            "free_courses": [],
            "paid_courses": [],
            "skill_coverage": {},
            "uncovered_skills": [],
            "coverage_percentage": 100
        }
    
    # Use top 3 from priority-ranked list (most critical first)
    top_critical_skills = target_skills[:3] if target_skills else []
    
    print(f"Debug: Recommending courses for {len(target_skills)} missing skills")
    print(f"Debug: Top 3 CRITICAL skills (must be covered): {top_critical_skills}")
    print(f"Debug: All missing skills: {target_skills[:10]}{'...' if len(target_skills) > 10 else ''}")
    
    # Get recommendations from MongoDB with pre-calculated skill weights
    recommendations = get_course_recommendations(
        skills=target_skills,
        require_free=require_free,
        require_paid=require_paid,
        max_free=max_free,
        max_paid=max_paid,
        skill_weights=skill_weights_to_use
    )
    
    return recommendations


def recommend_courses_for_job_skills(
    job_skills: List[str],
    require_free: bool = False,
    require_paid: bool = False,
    max_free: int = 1,
    max_paid: int = 1,
) -> dict:
    """
    Fallback recommender that uses **job/domain skills** (e.g., "Data Analysis",
    "Machine Learning") instead of missing skills.

    This is used when we fail to find any courses for the missing skills but
    still want to recommend something relevant to the core of the job.

    Args:
        job_skills: List of skills/keywords derived from the job (title/domain).
        require_free: If True, only return free courses.
        require_paid: If True, only return paid courses.
        max_free: Max number of free courses to return.
        max_paid: Max number of paid courses to return.

    Returns:
        Dictionary with the same structure as `recommend_courses_from_gaps`.
    """
    # Clean and deduplicate skills
    skills: List[str] = []
    seen = set()
    for s in job_skills or []:
        if not s:
            continue
        key = str(s).strip().lower()
        if key and key not in seen:
            skills.append(str(s).strip())
            seen.add(key)

    if not skills:
        return {
            "free_courses": [],
            "paid_courses": [],
            "skill_coverage": {},
            "uncovered_skills": [],
            "coverage_percentage": 0
        }

    # Use the generic skill-based course recommender
    recommendations = get_course_recommendations(
        skills=skills,
        require_free=require_free,
        require_paid=require_paid,
        max_free=max_free,
        max_paid=max_paid,
        skill_weights=None,  # treat all job skills equally for fallback
    )

    return recommendations


# ---------- Public function for generate_report.py orchestrator ----------
def get_course_recommendations_with_fallback(
    missing_skills_data: dict,
    job_skills_json: dict,
    role: str = "Target Role",
    match_scores: dict = None
) -> dict:
    """
    Get course recommendations with fallback logic.
    
    Primary: Recommend courses based on missing skills (gaps) - uses flat skill lists.
    Fallback: If no courses found, recommend based on job skills. The fallback gracefully
    handles both flat skill lists and old bucketed dict structures (any bucket names).
    
    Args:
        missing_skills_data: Dictionary containing gaps and skill_weights from score_match.
            Gaps are flat lists: {"required": [skills], "preferred": [skills]}
        job_skills_json: Job skills JSON (for fallback). Can have flat lists or bucketed dicts.
        role: Target role name
        match_scores: Full match_scores dict (for accessing pre-ranked missing skills)
    
    Returns:
        Dictionary with course recommendations: {
            "free_courses": [...],
            "paid_courses": [...],
            "skill_coverage": {...},
            "uncovered_skills": [...],
            "coverage_percentage": ...
        }
    """
    gaps = missing_skills_data.get("gaps", {})
    skill_weights_dict = missing_skills_data.get("skill_weights", {})
    
    # Use required gaps first, fall back to preferred if no required gaps
    gaps_to_use = gaps.get("required", [])
    skill_weights_to_use = skill_weights_dict.get("required", {})
    
    if not gaps_to_use:
        gaps_to_use = gaps.get("preferred", [])
        skill_weights_to_use = skill_weights_dict.get("preferred", {})
    
    # Use pre-ranked missing skills from match_scores (already ranked by priority)
    if match_scores:
        missing_required = match_scores.get("missing_skills", {}).get("required", [])
        missing_preferred = match_scores.get("missing_skills", {}).get("preferred", [])
        ranked_skills = missing_required if gaps.get("required", []) else missing_preferred
    else:
        # Fallback: rank by weights (shouldn't happen if match_scores is passed)
        ranked_skills = sorted(gaps_to_use, key=lambda s: skill_weights_to_use.get(s, 0.5), reverse=True)
    
    # First: try based on missing skills (gaps) - get 1 paid course initially
    # Pass ranked_skills to preserve priority order for course recommendations
    recommendations = recommend_courses_from_gaps(
        missing_skills_data=missing_skills_data,
        role=role,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1,
        ranked_skills=ranked_skills  # Pass priority-ranked skills to preserve order
    )

    free_courses = recommendations.get("free_courses") or []
    paid_courses = recommendations.get("paid_courses") or []
    
    # If we found at least one course, return the recommendations
    if free_courses or paid_courses:
        print(f"Debug: Returning recommendations with {len(free_courses)} free and {len(paid_courses)} paid courses")
        return recommendations

    # Second: FALLBACK – recommend based on job/domain skills
    job_required_skills_raw = (job_skills_json.get("required", {}) or {}).get("skills", []) or []
    job_preferred_skills_raw = (job_skills_json.get("preferred", {}) or {}).get("skills", []) or []
    
    # Build flat list of job skills (handle both bucketed dicts and flat lists)
    job_skill_list = []
    seen = set()
    
    # Helper to flatten skills (handles both dict with buckets and flat list)
    def flatten_skills(skills_input):
        # Case 1: already a flat list of skills
        if isinstance(skills_input, list):
            return skills_input
        
        # Case 2: dict of buckets -> lists of skills (any bucket names)
        if isinstance(skills_input, dict):
            flattened = []
            for bucket_skills in skills_input.values():
                if isinstance(bucket_skills, list):
                    flattened.extend(bucket_skills)
            return flattened
        
        # Fallback: unknown type
        return []
    
    # Flatten required and preferred skills
    required_flat = flatten_skills(job_required_skills_raw)
    preferred_flat = flatten_skills(job_preferred_skills_raw)
    
    # Combine into single flat list of unique skills
    for skill in required_flat + preferred_flat:
        if not skill:
            continue
        key = str(skill).strip().lower()
        if key and key not in seen:
            job_skill_list.append(str(skill).strip())
            seen.add(key)

    # If there are no job skills to fall back on, return empty as-is
    if not job_skill_list:
        return recommendations

    fallback_recommendations = recommend_courses_for_job_skills(
        job_skills=job_skill_list,
        require_free=False,
        require_paid=False,
        max_free=1,
        max_paid=1,
    )

    return fallback_recommendations
