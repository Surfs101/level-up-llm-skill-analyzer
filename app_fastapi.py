# app_fastapi.py
# FastAPI web application for resume-job matching

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from pathlib import Path
from generate_report import generate_report
from pdf_resume_parser import PDFToTextConverter

app = FastAPI(title="Resume-Job Match Analyzer", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume-Job Match Analyzer (FastAPI)</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 1.1em;
        }
        input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px dashed #667eea;
            border-radius: 8px;
            background: #f8f9ff;
            font-size: 1em;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            font-family: inherit;
            resize: vertical;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.2em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
            font-size: 1.1em;
        }
        .error {
            color: #e74c3c;
            background: #fee;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            border-left: 4px solid #e74c3c;
        }
        .success {
            color: #27ae60;
            background: #efe;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            border-left: 4px solid #27ae60;
        }
        .metrics {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 8px;
        }
        .metrics h2 {
            margin-bottom: 15px;
            color: #333;
        }
        .metrics p {
            margin: 10px 0;
            font-size: 1.1em;
        }
        .report-section {
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .report-section h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .skills-list {
            list-style: none;
            padding-left: 0;
        }
        .skills-list li {
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        .skills-list li:last-child {
            border-bottom: none;
        }
        .course-card, .project-card {
            margin: 15px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .course-card h4, .project-card h4 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .course-card .detail, .project-card .detail {
            margin: 10px 0;
            line-height: 1.6;
        }
        .course-card .detail strong, .project-card .detail strong {
            color: #555;
            display: inline-block;
            min-width: 150px;
        }
        .course-card .description, .project-card .description {
            margin: 15px 0;
            padding: 15px;
            background: #f8f9ff;
            border-radius: 5px;
            line-height: 1.8;
        }
        .course-card ul, .project-card ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .course-card ul li, .project-card ul li {
            margin: 5px 0;
        }
        .clickable-skill-header {
            cursor: pointer;
            user-select: none;
            padding: 8px;
            border-radius: 5px;
            transition: background-color 0.2s;
        }
        .clickable-skill-header:hover {
            background-color: #e8e8ff;
        }
        .skill-details {
            display: none;
            margin-top: 10px;
            padding: 15px;
            background: #f0f0f5;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }
        .skill-details.expanded {
            display: block;
        }
        .skill-item {
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }
        .skill-matched {
            background-color: #d4edda;
            color: #155724;
            border-left: 3px solid #28a745;
        }
        .skill-missing {
            background-color: #f8d7da;
            color: #721c24;
            border-left: 3px solid #dc3545;
        }
        .skill-matched::before {
            content: "✅ ";
            font-weight: bold;
        }
        .skill-missing::before {
            content: "❌ ";
            font-weight: bold;
        }
        .skill-section-title {
            font-weight: 600;
            margin: 10px 0 5px 0;
            color: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Resume-Job Match Analyzer</h1>
        <form id="matchForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="resume">Upload Resume (PDF):</label>
                <input type="file" id="resume" name="resume" accept=".pdf" required>
            </div>
            <div class="form-group">
                <label for="job_description">Job Description:</label>
                <textarea id="job_description" name="job_description" 
                          placeholder="Paste the job description here..." required></textarea>
            </div>
            <button type="submit" id="submitBtn">Analyze Match</button>
        </form>
        <div class="loading" id="loading">⏳ Processing your resume and job description...</div>
        <div id="result"></div>
    </div>

    <script>
        document.getElementById('matchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            const resumeFile = document.getElementById('resume').files[0];
            const jobDescription = document.getElementById('job_description').value;
            
            if (!resumeFile || !jobDescription) {
                alert('Please upload a resume and provide a job description.');
                return;
            }
            
            formData.append('resume', resumeFile);
            formData.append('job_description', jobDescription);
            
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            submitBtn.disabled = true;
            loading.style.display = 'block';
            result.innerHTML = '';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Display metrics
                    let html = `
                        <div class="success">✅ Analysis complete!</div>
                        <div class="metrics">
                            <h2>Key Metrics</h2>
                            <p><strong>Overall Match Score:</strong> ${data.overall_score.weighted_score.toFixed(2)}%</p>
                            <div class="clickable-skill-header" onclick="toggleSkillDetails('required-skills')">
                                <strong>📋 Required Skills Coverage:</strong> ${data.required_skills.match_score.toFixed(2)}% 
                                (${data.required_skills.covered_count}/${data.required_skills.total_count}) 
                                <span style="font-size: 0.9em; color: #667eea;">[Click to expand]</span>
                            </div>
                            <div id="required-skills" class="skill-details">
                                ${data.required_skills.covered_skills && data.required_skills.covered_skills.length > 0 ? 
                                    `<div class="skill-section-title">✅ Matched Skills (${data.required_skills.covered_skills.length}):</div>
                                    ${data.required_skills.covered_skills.map(skill => `<div class="skill-item skill-matched">${skill}</div>`).join('')}` : 
                                    '<div class="skill-section-title">No matched skills</div>'}
                                ${data.required_skills.missing_skills && data.required_skills.missing_skills.length > 0 ? 
                                    `<div class="skill-section-title">❌ Missing Skills (${data.required_skills.missing_skills.length}):</div>
                                    ${data.required_skills.missing_skills.map(skill => `<div class="skill-item skill-missing">${skill}</div>`).join('')}` : 
                                    '<div class="skill-section-title">✅ All required skills covered!</div>'}
                            </div>
                            <div class="clickable-skill-header" onclick="toggleSkillDetails('preferred-skills')" style="margin-top: 15px;">
                                <strong>⭐ Preferred Skills Coverage:</strong> ${data.preferred_skills.match_score.toFixed(2)}% 
                                (${data.preferred_skills.covered_count}/${data.preferred_skills.total_count}) 
                                <span style="font-size: 0.9em; color: #667eea;">[Click to expand]</span>
                            </div>
                            <div id="preferred-skills" class="skill-details">
                                ${data.preferred_skills.covered_skills && data.preferred_skills.covered_skills.length > 0 ? 
                                    `<div class="skill-section-title">✅ Matched Skills (${data.preferred_skills.covered_skills.length}):</div>
                                    ${data.preferred_skills.covered_skills.map(skill => `<div class="skill-item skill-matched">${skill}</div>`).join('')}` : 
                                    '<div class="skill-section-title">No matched skills</div>'}
                                ${data.preferred_skills.missing_skills && data.preferred_skills.missing_skills.length > 0 ? 
                                    `<div class="skill-section-title">❌ Missing Skills (${data.preferred_skills.missing_skills.length}):</div>
                                    ${data.preferred_skills.missing_skills.map(skill => `<div class="skill-item skill-missing">${skill}</div>`).join('')}` : 
                                    '<div class="skill-section-title">✅ All preferred skills covered!</div>'}
                            </div>
                        </div>
                    `;
                    
                    // Note: Required and Preferred skills are now shown in the expandable sections above
                    
                    // Course recommendations
                    if (data.course_recommendations) {
                        html += `<div class="report-section"><h3>📚 Course Recommendations</h3>`;
                        
                        // Free Course
                        if (data.course_recommendations.free_courses && data.course_recommendations.free_courses.length > 0) {
                            const free = data.course_recommendations.free_courses[0];
                            html += `
                                <div class="course-card">
                                    <h4>🆓 Free Course: ${free.title || 'N/A'}</h4>
                                    <div class="detail"><strong>Platform:</strong> ${free.platform || 'N/A'}</div>
                                    <div class="detail"><strong>Duration:</strong> ${free.duration || 'N/A'}</div>
                                    <div class="detail"><strong>Difficulty:</strong> ${free.difficulty || 'N/A'}</div>
                                    <div class="detail"><strong>Cost:</strong> ${free.cost || 'Free'}</div>
                                    ${free.link ? `<div class="detail"><strong>Link:</strong> <a href="${free.link}" target="_blank">${free.link}</a></div>` : ''}
                                    ${free.skills_covered && free.skills_covered.length > 0 ? 
                                        `<div class="detail"><strong>Skills Covered:</strong> <ul><li>${free.skills_covered.join('</li><li>')}</li></ul></div>` : ''}
                                    ${free.additional_skills && free.additional_skills.length > 0 ? 
                                        `<div class="detail"><strong>Additional Skills:</strong> <ul><li>${free.additional_skills.join('</li><li>')}</li></ul></div>` : ''}
                                    ${free.description ? `<div class="description"><strong>Description:</strong><br>${free.description}</div>` : ''}
                                    ${free.why_efficient ? `<div class="detail"><strong>Why This Course:</strong> ${free.why_efficient}</div>` : ''}
                                </div>
                            `;
                        } else {
                            html += `<div class="course-card"><p>No free course available</p></div>`;
                        }
                        
                        // Paid Course
                        if (data.course_recommendations.paid_courses && data.course_recommendations.paid_courses.length > 0) {
                            const paid = data.course_recommendations.paid_courses[0];
                            html += `
                                <div class="course-card">
                                    <h4>💰 Paid Course: ${paid.title || 'N/A'}</h4>
                                    <div class="detail"><strong>Platform:</strong> ${paid.platform || 'N/A'}</div>
                                    <div class="detail"><strong>Duration:</strong> ${paid.duration || 'N/A'}</div>
                                    <div class="detail"><strong>Difficulty:</strong> ${paid.difficulty || 'N/A'}</div>
                                    <div class="detail"><strong>Cost:</strong> ${paid.cost || 'N/A'}</div>
                                    ${paid.link ? `<div class="detail"><strong>Link:</strong> <a href="${paid.link}" target="_blank">${paid.link}</a></div>` : ''}
                                    ${paid.skills_covered && paid.skills_covered.length > 0 ? 
                                        `<div class="detail"><strong>Skills Covered:</strong> <ul><li>${paid.skills_covered.join('</li><li>')}</li></ul></div>` : ''}
                                    ${paid.additional_skills && paid.additional_skills.length > 0 ? 
                                        `<div class="detail"><strong>Additional Skills:</strong> <ul><li>${paid.additional_skills.join('</li><li>')}</li></ul></div>` : ''}
                                    ${paid.description ? `<div class="description"><strong>Description:</strong><br>${paid.description}</div>` : ''}
                                    ${paid.why_efficient ? `<div class="detail"><strong>Why This Course:</strong> ${paid.why_efficient}</div>` : ''}
                                </div>
                            `;
                        } else {
                            html += `<div class="course-card"><p>No paid course available</p></div>`;
                        }
                        
                        html += `</div>`;
                    }
                    
                    // Project recommendations
                    if (data.project_recommendations && Object.keys(data.project_recommendations).length > 0) {
                        html += `<div class="report-section"><h3>🚀 Project Recommendations</h3>`;
                        for (const [track, projects] of Object.entries(data.project_recommendations)) {
                            html += `<h4 style="color: #667eea; margin-top: 20px;">Track: ${track}</h4>`;
                            projects.forEach((project, idx) => {
                                html += `
                                    <div class="project-card">
                                        <h4>${idx + 1}. ${project.title || 'Untitled Project'}</h4>
                                        <div class="detail"><strong>Difficulty:</strong> ${project.difficulty || 'N/A'}</div>
                                        <div class="detail"><strong>Estimated Time:</strong> ${project.estimated_time || 'N/A'}</div>
                                        ${project.description ? `<div class="description"><strong>Description:</strong><br>${project.description}</div>` : ''}
                                        ${project.key_features && project.key_features.length > 0 ? 
                                            `<div class="detail"><strong>Key Features:</strong> <ul><li>${project.key_features.join('</li><li>')}</li></ul></div>` : ''}
                                        ${project.skills_demonstrated && project.skills_demonstrated.length > 0 ? 
                                            `<div class="detail"><strong>Skills Demonstrated:</strong> <ul><li>${project.skills_demonstrated.join('</li><li>')}</li></ul></div>` : ''}
                                        ${project.technologies && project.technologies.length > 0 ? 
                                            `<div class="detail"><strong>Technologies:</strong> <ul><li>${project.technologies.join('</li><li>')}</li></ul></div>` : ''}
                                        ${project.portfolio_impact ? `<div class="detail"><strong>Portfolio Impact:</strong> ${project.portfolio_impact}</div>` : ''}
                                        ${project.bonus_challenges && project.bonus_challenges.length > 0 ? 
                                            `<div class="detail"><strong>Bonus Challenges:</strong> <ul><li>${project.bonus_challenges.join('</li><li>')}</li></ul></div>` : ''}
                                    </div>
                                `;
                            });
                        }
                        html += `</div>`;
                    }
                    
                    result.innerHTML = html;
                    console.log('Full Report:', data);
                } else {
                    result.innerHTML = `<div class="error">❌ Error: ${data.detail || 'Unknown error occurred'}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
            } finally {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            }
        });
        
        // Toggle function for expandable skill details
        function toggleSkillDetails(id) {
            const element = document.getElementById(id);
            if (element) {
                element.classList.toggle('expanded');
            }
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Render the main page."""
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_description: str = Form(..., description="Job description text")
):
    """
    Analyze resume and job description match.
    
    - **resume**: PDF file containing the resume
    - **job_description**: Text description of the job posting
    
    Returns a comprehensive report with:
    - Overall match score
    - Required skills analysis
    - Preferred skills analysis
    - Course recommendations
    - Project recommendations
    """
    try:
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
        
        if not job_description.strip():
            raise HTTPException(status_code=400, detail="Job description is required")
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, resume.filename)
        
        with open(temp_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        try:
            # Convert PDF to text
            converter = PDFToTextConverter(temp_path)
            if not converter.convert():
                raise HTTPException(status_code=500, detail="Failed to extract text from PDF")
            
            resume_text = converter.cleaned_text
            if not resume_text:
                raise HTTPException(
                    status_code=500, 
                    detail="No text extracted from PDF. The PDF might be image-based or corrupted."
                )
            
            # Generate report
            report = generate_report(
                resume_text=resume_text,
                job_description_text=job_description,
                role_label="Target Role"
            )
            
            return JSONResponse(content=report)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Resume-Job Match Analyzer"}


if __name__ == '__main__':
    import uvicorn
    print("🚀 FastAPI app starting on http://127.0.0.1:8000")
    print("📖 API documentation available at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

