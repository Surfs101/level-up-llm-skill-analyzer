# generate_report.py
# Pipeline orchestrator that generates a comprehensive career matching report
# Takes resume text and job description text as inputs, returns structured report

from typing import Dict, Any
import json

from score_skills_match import score_match, parse_weights
from extract_skills import extract_resume_skills_from_text
from extract_job_skills import extract_job_skills_from_text
from recommend_courses import get_course_recommendations_with_fallback
from recommend_projects import get_project_recommendations


def generate_report(
    resume_text: str,
    job_description_text: str,
    role_label: str = "Target Role",
    weights: str = "required=1.0,preferred=0.5",
    progress_callback=None
) -> Dict[str, Any]:
    """
    Generate comprehensive career matching report.
    
    Args:
        resume_text: Raw text content from resume (PDF converted to text)
        job_description_text: Job description text
        role_label: Label for the role (e.g., "MLOps Engineer")
        weights: Weights string for scoring (e.g., "required=1.0,preferred=0.5")
    
    Returns:
        Dictionary containing comprehensive report with:
        - overall_score: Overall resume skill match score
        - required_skills: Match score and missing skills for required
        - preferred_skills: Match score and missing skills for preferred
        - course_recommendations: Course recommendations with all info
        - project_recommendations: Project recommendations
    """
    
    # Step 1: Extract resume skills
    step_msg = "Extracting skills from resume..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    resume_skills_json = extract_resume_skills_from_text(resume_text)
    
    # Step 2: Extract job skills
    step_msg = "Extracting skills from job description..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    job_skills_json = extract_job_skills_from_text(job_description_text)
    
    # Step 3: Score match
    step_msg = "Computing skills match scores and analyzing skill priorities..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    w_req, w_pref = parse_weights(weights)
    match_scores = score_match(resume_skills_json, job_skills_json, w_req, w_pref, job_description_text)
    
    # Step 4: Prepare missing_skills_data
    gaps = match_scores.get("gaps", {})
    skill_weights = match_scores.get("skill_weights", {})
    missing_skills_data = {
        "gaps": gaps,
        "skill_weights": skill_weights
    }
    
    # Step 5: Get course recommendations
    step_msg = "Generating course recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    course_recommendations = get_course_recommendations_with_fallback(
        missing_skills_data,
        job_skills_json,
        role_label,
        match_scores
    )
    
    # Step 6: Get project recommendations
    step_msg = "Generating project recommendations..."
    print(step_msg)
    if progress_callback:
        progress_callback(step_msg)
    project_recommendations = get_project_recommendations(
        resume_skills_json,
        job_description_text,
        course_recommendations,
        role_label
    )
    
    # Compile final report
    report = {
        "is_grad_student_job": job_skills_json.get("is_grad_student_job", False),
        "overall_score": {
            "weighted_score": match_scores["summary"]["weighted_score"],
            "required_coverage_pct": match_scores["summary"]["required_coverage_pct"],
            "preferred_coverage_pct": match_scores["summary"]["preferred_coverage_pct"],
            "overall_jaccard_pct": match_scores["summary"]["overall_jaccard_pct"]
        },
        "required_skills": {
            "match_score": match_scores["summary"]["required_coverage_pct"],
            "covered_count": match_scores["summary"]["counts"]["required"]["covered"],
            "total_count": match_scores["summary"]["counts"]["required"]["total"],
            "covered_skills": match_scores["covered_skills"]["required"],
            "missing_skills": match_scores["missing_skills"]["required"]
        },
        "preferred_skills": {
            "match_score": match_scores["summary"]["preferred_coverage_pct"],
            "covered_count": match_scores["summary"]["counts"]["preferred"]["covered"],
            "total_count": match_scores["summary"]["counts"]["preferred"]["total"],
            "covered_skills": match_scores["covered_skills"]["preferred"],
            "missing_skills": match_scores["missing_skills"]["preferred"]
        },
        "course_recommendations": course_recommendations,
        "project_recommendations": project_recommendations
    }
    
    print("✅ Report generation complete!")
    return report


if __name__ == "__main__":
    # Example usage for testing
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <resume_text_file> <job_description_file> [role_label]")
        sys.exit(1)
    
    resume_file = sys.argv[1]
    job_file = sys.argv[2]
    role_label = sys.argv[3] if len(sys.argv) > 3 else "Target Role"
    
    with open(resume_file, "r", encoding="utf-8") as f:
        resume_text = f.read()
    
    with open(job_file, "r", encoding="utf-8") as f:
        job_text = f.read()
    
    report = generate_report(resume_text, job_text, role_label)
    
    # Save report
    output_file = "final_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Report saved to {output_file}")
    print(f"\nOverall Score: {report['overall_score']['weighted_score']}%")
    print(f"Required Skills Match: {report['required_skills']['match_score']}%")
    print(f"Preferred Skills Match: {report['preferred_skills']['match_score']}%")

