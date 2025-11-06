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

app = FastAPI(title="TalentFit Intelligence", version="1.0.0")

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
    <title>TalentFit Intelligence – AI-Powered Candidate Matching</title>
    <style>
        :root {
            --bg-primary: #0a0e27;
            --bg-secondary: #13182e;
            --bg-tertiary: #1a1f3a;
            --bg-card: rgba(26, 31, 58, 0.6);
            --accent-primary: #5b8cff;
            --accent-secondary: #7c4dff;
            --accent-success: #18c79c;
            --accent-warning: #ffb020;
            --accent-error: #ff6b6b;
            --text-primary: #e7ecff;
            --text-secondary: #a6b0cf;
            --text-muted: #6b7280;
            --border-color: rgba(91, 140, 255, 0.15);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.5);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Inter', 'Helvetica Neue', Arial, sans-serif;
            background: radial-gradient(ellipse at top left, rgba(91, 140, 255, 0.1) 0%, transparent 50%),
                        radial-gradient(ellipse at bottom right, rgba(124, 77, 255, 0.1) 0%, transparent 50%),
                        var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }

        .app-container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 24px;
        }

        /* Top Navigation Bar */
        .navbar {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 16px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow-md);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 18px;
            color: white;
            box-shadow: 0 4px 12px rgba(91, 140, 255, 0.3);
        }

        .brand-text {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .badge {
            padding: 6px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        /* Main Layout */
        .main-layout {
            display: grid;
            grid-template-columns: 420px 1fr;
            gap: 24px;
        }

        /* Card Component */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            overflow: hidden;
        }

        .card-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .card-title {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .card-body {
            padding: 24px;
        }

        /* Form Styles */
        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        input[type="file"] {
            width: 100%;
            padding: 14px;
            background: var(--bg-tertiary);
            border: 2px dashed var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        input[type="file"]:hover {
            border-color: var(--accent-primary);
            background: rgba(91, 140, 255, 0.05);
        }

        textarea {
            width: 100%;
            min-height: 200px;
            padding: 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            transition: all 0.3s ease;
        }

        textarea:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(91, 140, 255, 0.1);
        }

        .btn-primary {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border: none;
            border-radius: var(--radius-md);
            color: white;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 24px rgba(91, 140, 255, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 12px 32px rgba(91, 140, 255, 0.4);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .loading {
            display: none;
            padding: 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            margin-top: 16px;
            text-align: center;
            color: var(--accent-primary);
            font-weight: 600;
        }

        /* Results Section */
        .results-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .alert {
            padding: 16px 20px;
            border-radius: var(--radius-md);
            border: 1px solid;
            font-weight: 600;
        }

        .alert-success {
            background: rgba(24, 199, 156, 0.1);
            border-color: rgba(24, 199, 156, 0.3);
            color: var(--accent-success);
        }

        .alert-error {
            background: rgba(255, 107, 107, 0.1);
            border-color: rgba(255, 107, 107, 0.3);
            color: var(--accent-error);
        }

        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .metric-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 20px;
            text-align: center;
        }

        .metric-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* Skills Section */
        .skills-section {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 20px;
            margin-bottom: 20px;
        }

        .skills-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            padding: 12px;
            border-radius: var(--radius-sm);
            transition: background 0.2s;
        }

        .skills-header:hover {
            background: rgba(91, 140, 255, 0.05);
        }

        .skills-header-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .skills-header-stats {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .skills-details {
            display: none;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
        }

        .skills-details.expanded {
            display: block;
        }

        .skill-tag {
            display: inline-block;
            padding: 8px 14px;
            margin: 6px 6px 6px 0;
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 600;
        }

        .skill-matched {
            background: rgba(24, 199, 156, 0.15);
            border: 1px solid rgba(24, 199, 156, 0.3);
            color: var(--accent-success);
        }

        .skill-missing {
            background: rgba(255, 107, 107, 0.15);
            border: 1px solid rgba(255, 107, 107, 0.3);
            color: var(--accent-error);
        }

        .section-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 16px 0 12px 0;
        }

        /* Course & Project Cards */
        .content-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 24px;
            margin-bottom: 20px;
        }

        .content-card h4 {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 16px;
        }

        .content-card .detail {
            margin: 12px 0;
            font-size: 14px;
            color: var(--text-secondary);
        }

        .content-card .detail strong {
            color: var(--text-primary);
            font-weight: 600;
            display: inline-block;
            min-width: 140px;
        }

        .content-card .description {
            margin: 16px 0;
            padding: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            line-height: 1.8;
            color: var(--text-secondary);
        }

        .content-card ul {
            margin: 8px 0;
            padding-left: 24px;
        }

        .content-card ul li {
            margin: 6px 0;
            color: var(--text-secondary);
        }

        /* Project Badge */
        .project-badge {
            display: inline-block;
            padding: 10px 18px;
            border-radius: 24px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 16px;
        }

        .badge-current {
            background: linear-gradient(135deg, var(--accent-success), #20c997);
            color: white;
            box-shadow: 0 4px 12px rgba(24, 199, 156, 0.3);
        }

        .badge-missing {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            box-shadow: 0 4px 12px rgba(91, 140, 255, 0.3);
        }

        .project-card {
            border-left: 4px solid;
        }

        .project-card.current {
            border-left-color: var(--accent-success);
        }

        .project-card.missing {
            border-left-color: var(--accent-primary);
        }

        /* Responsive */
        @media (max-width: 1200px) {
            .main-layout {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 768px) {
            .app-container {
                padding: 16px;
            }
            .metrics-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <nav class="navbar">
            <div class="brand">
                <div class="brand-logo">TF</div>
                <div class="brand-text">TalentFit Intelligence</div>
            </div>
            <div class="nav-actions">
                <span class="badge">v1.0.0</span>
                <span class="badge">AI-Powered</span>
            </div>
        </nav>

        <div class="main-layout">
            <!-- Input Panel -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Candidate & Job Input</div>
                </div>
                <div class="card-body">
                    <form id="matchForm" enctype="multipart/form-data">
                        <div class="form-group">
                            <label for="resume">Upload Résumé (PDF)</label>
                            <input type="file" id="resume" name="resume" accept=".pdf" required>
                        </div>
                        <div class="form-group">
                            <label for="job_description">Job Description</label>
                            <textarea id="job_description" name="job_description" 
                                      placeholder="Paste the job description here..." required></textarea>
                        </div>
                        <button type="submit" id="submitBtn" class="btn-primary">Analyze Match</button>
                    </form>
                    <div class="loading" id="loading">⏳ Processing your résumé and job description...</div>
                </div>
            </div>

            <!-- Results Panel -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Analysis Results</div>
                    <div class="badge">Live</div>
                </div>
                <div class="card-body">
                    <div id="result" class="results-container"></div>
                </div>
            </div>
        </div>
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
                    let html = `
                        <div class="alert alert-success">✅ Analysis complete! Your comprehensive report is ready.</div>
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">Overall Match</div>
                                <div class="metric-value">${data.overall_score.weighted_score.toFixed(1)}%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Required Coverage</div>
                                <div class="metric-value">${data.required_skills.match_score.toFixed(1)}%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Preferred Coverage</div>
                                <div class="metric-value">${data.preferred_skills.match_score.toFixed(1)}%</div>
                            </div>
                        </div>
                    `;
                    
                    // Required Skills
                    html += `
                        <div class="skills-section">
                            <div class="skills-header" onclick="toggleSkillDetails('required-skills')">
                                <div>
                                    <div class="skills-header-title">📋 Required Skills Coverage</div>
                                    <div class="skills-header-stats">${data.required_skills.covered_count} of ${data.required_skills.total_count} skills matched</div>
                                </div>
                                <div style="color: var(--accent-primary);">▼</div>
                            </div>
                            <div id="required-skills" class="skills-details">
                                ${data.required_skills.covered_skills && data.required_skills.covered_skills.length > 0 ? 
                                    `<div class="section-title">✅ Matched Skills (${data.required_skills.covered_skills.length})</div>
                                    ${data.required_skills.covered_skills.map(skill => `<span class="skill-tag skill-matched">${skill}</span>`).join('')}` : 
                                    '<div class="section-title">No matched skills</div>'}
                                ${data.required_skills.missing_skills && data.required_skills.missing_skills.length > 0 ? 
                                    `<div class="section-title" style="margin-top: 20px;">❌ Missing Skills (${data.required_skills.missing_skills.length})</div>
                                    ${data.required_skills.missing_skills.map(skill => `<span class="skill-tag skill-missing">${skill}</span>`).join('')}` : 
                                    '<div class="section-title" style="margin-top: 20px;">✅ All required skills covered!</div>'}
                            </div>
                        </div>
                    `;
                    
                    // Preferred Skills
                    html += `
                        <div class="skills-section">
                            <div class="skills-header" onclick="toggleSkillDetails('preferred-skills')">
                                <div>
                                    <div class="skills-header-title">⭐ Preferred Skills Coverage</div>
                                    <div class="skills-header-stats">${data.preferred_skills.covered_count} of ${data.preferred_skills.total_count} skills matched</div>
                                </div>
                                <div style="color: var(--accent-primary);">▼</div>
                            </div>
                            <div id="preferred-skills" class="skills-details">
                                ${data.preferred_skills.covered_skills && data.preferred_skills.covered_skills.length > 0 ? 
                                    `<div class="section-title">✅ Matched Skills (${data.preferred_skills.covered_skills.length})</div>
                                    ${data.preferred_skills.covered_skills.map(skill => `<span class="skill-tag skill-matched">${skill}</span>`).join('')}` : 
                                    '<div class="section-title">No matched skills</div>'}
                                ${data.preferred_skills.missing_skills && data.preferred_skills.missing_skills.length > 0 ? 
                                    `<div class="section-title" style="margin-top: 20px;">❌ Missing Skills (${data.preferred_skills.missing_skills.length})</div>
                                    ${data.preferred_skills.missing_skills.map(skill => `<span class="skill-tag skill-missing">${skill}</span>`).join('')}` : 
                                    '<div class="section-title" style="margin-top: 20px;">✅ All preferred skills covered!</div>'}
                            </div>
                        </div>
                    `;
                    
                    // Course Recommendations
                    if (data.course_recommendations) {
                        html += `<div class="content-card"><h4>📚 Course Recommendations</h4>`;
                        
                        if (data.course_recommendations.free_courses && data.course_recommendations.free_courses.length > 0) {
                            const free = data.course_recommendations.free_courses[0];
                            html += `
                                <div style="margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid var(--border-color);">
                                    <h4 style="color: var(--accent-success); margin-bottom: 12px;">🆓 Free Course: ${free.title || 'N/A'}</h4>
                                    <div class="detail"><strong>Platform:</strong> ${free.platform || 'N/A'}</div>
                                    <div class="detail"><strong>Duration:</strong> ${free.duration || 'N/A'}</div>
                                    <div class="detail"><strong>Difficulty:</strong> ${free.difficulty || 'N/A'}</div>
                                    <div class="detail"><strong>Cost:</strong> ${free.cost || 'Free'}</div>
                                    ${free.link ? `<div class="detail"><strong>Link:</strong> <a href="${free.link}" target="_blank" style="color: var(--accent-primary);">${free.link}</a></div>` : ''}
                                    ${free.skills_covered && free.skills_covered.length > 0 ? 
                                        `<div class="detail"><strong>Skills Covered:</strong> <ul><li>${free.skills_covered.join('</li><li>')}</li></ul></div>` : ''}
                                    ${free.description ? `<div class="description">${free.description}</div>` : ''}
                                    ${free.why_efficient ? `<div class="detail"><strong>Why This Course:</strong> ${free.why_efficient}</div>` : ''}
                                </div>
                            `;
                        }
                        
                        if (data.course_recommendations.paid_courses && data.course_recommendations.paid_courses.length > 0) {
                            const paid = data.course_recommendations.paid_courses[0];
                            html += `
                                <div>
                                    <h4 style="color: var(--accent-primary); margin-bottom: 12px;">💰 Paid Course: ${paid.title || 'N/A'}</h4>
                                    <div class="detail"><strong>Platform:</strong> ${paid.platform || 'N/A'}</div>
                                    <div class="detail"><strong>Duration:</strong> ${paid.duration || 'N/A'}</div>
                                    <div class="detail"><strong>Difficulty:</strong> ${paid.difficulty || 'N/A'}</div>
                                    <div class="detail"><strong>Cost:</strong> ${paid.cost || 'N/A'}</div>
                                    ${paid.link ? `<div class="detail"><strong>Link:</strong> <a href="${paid.link}" target="_blank" style="color: var(--accent-primary);">${paid.link}</a></div>` : ''}
                                    ${paid.skills_covered && paid.skills_covered.length > 0 ? 
                                        `<div class="detail"><strong>Skills Covered:</strong> <ul><li>${paid.skills_covered.join('</li><li>')}</li></ul></div>` : ''}
                                    ${paid.description ? `<div class="description">${paid.description}</div>` : ''}
                                    ${paid.why_efficient ? `<div class="detail"><strong>Why This Course:</strong> ${paid.why_efficient}</div>` : ''}
                                </div>
                            `;
                        }
                        
                        html += `</div>`;
                    }
                    
                    // Project Recommendations
                    if (data.project_recommendations && Object.keys(data.project_recommendations).length > 0) {
                        html += `<div class="content-card"><h4>🚀 Project Recommendations</h4>`;
                        for (const [track, projects] of Object.entries(data.project_recommendations)) {
                            html += `<div style="margin-bottom: 24px;"><div style="color: var(--accent-primary); font-weight: 600; margin-bottom: 16px;">Track: ${track}</div>`;
                            projects.forEach((project, idx) => {
                                const isCurrentSkills = idx === 0;
                                const badgeText = isCurrentSkills ? '✨ Build with Your Current Skills' : '🎯 Learn Missing Skills & Fill the Gap';
                                const badgeClass = isCurrentSkills ? 'badge-current' : 'badge-missing';
                                const cardClass = isCurrentSkills ? 'current' : 'missing';
                                
                                html += `
                                    <div style="margin-bottom: 24px;">
                                        <span class="project-badge ${badgeClass}">${badgeText}</span>
                                        <div class="content-card project-card ${cardClass}">
                                            <h4>${project.title || 'Untitled Project'}</h4>
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
                                    </div>
                                `;
                            });
                            html += `</div>`;
                        }
                        html += `</div>`;
                    }
                    
                    result.innerHTML = html;
                    console.log('Full Report:', data);
                } else {
                    result.innerHTML = `<div class="alert alert-error">❌ Error: ${data.detail || 'Unknown error occurred'}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="alert alert-error">❌ Error: ${error.message}</div>`;
            } finally {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            }
        });
        
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
