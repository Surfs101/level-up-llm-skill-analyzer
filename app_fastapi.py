# app_fastapi.py
# FastAPI web application for resume-job matching

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from typing import Optional
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import json
import asyncio
import threading
import hashlib
import time
from pathlib import Path
from generate_report import generate_report
from generate_cover_letter import generate_cover_letter_from_text
from pdf_resume_parser import PDFToTextConverter

# Request deduplication cache (simple in-memory cache)
_request_cache = {}
_cache_lock = threading.Lock()
_cache_ttl = 60  # Cache for 60 seconds

# Try to import docx support
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("Warning: python-docx not installed. Word document (.docx) support will be unavailable.")

app = FastAPI(title="skillbridge.AI", version="1.0.0")

# Template support
templates = Jinja2Templates(directory="templates")


def extract_text_from_template_file(file_path: str, filename: str) -> str:
    """
    Extract text from a template file (supports .txt, .docx, .pdf).
    
    Args:
        file_path: Path to the uploaded file
        filename: Original filename (used to determine file type)
    
    Returns:
        Extracted text content as string
    
    Raises:
        ValueError: If file type is not supported or extraction fails
    """
    file_ext = os.path.splitext(filename.lower())[1]
    
    if file_ext in ['.txt', '.text']:
        # Plain text file
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    
    elif file_ext == '.docx':
        # Word document
        if not DOCX_AVAILABLE:
            raise ValueError("Word document (.docx) support requires python-docx. Install with: pip install python-docx")
        
        try:
            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise ValueError(f"Failed to extract text from Word document: {str(e)}")
    
    elif file_ext == '.pdf':
        # PDF file - reuse existing PDF parser
        try:
            converter = PDFToTextConverter(file_path)
            if not converter.convert():
                raise ValueError("Failed to extract text from PDF")
            return converter.cleaned_text
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    else:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported types: .txt, .docx, .pdf")

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

        .nav-buttons {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-btn {
            padding: 8px 16px;
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            display: inline-block;
        }
        
        .nav-btn:visited {
            color: var(--text-secondary);
        }
        
        .nav-btn.active:visited {
            color: white;
        }

        .nav-btn:hover {
            border-color: var(--accent-primary);
            color: var(--accent-primary);
            background: rgba(91, 140, 255, 0.05);
        }

        .nav-btn.active {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-color: var(--accent-primary);
            color: white;
            box-shadow: 0 4px 12px rgba(91, 140, 255, 0.3);
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

        /* Hero Section */
        .hero-section {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 48px 40px;
            margin-bottom: 32px;
            text-align: center;
            box-shadow: var(--shadow-md);
        }

        .hero-title {
            font-size: 42px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 16px;
            line-height: 1.2;
        }

        .hero-subtitle {
            font-size: 18px;
            color: var(--text-secondary);
            max-width: 700px;
            margin: 0 auto 24px;
            line-height: 1.6;
        }

        .hero-features {
            display: flex;
            justify-content: center;
            gap: 32px;
            flex-wrap: wrap;
            margin-top: 32px;
        }

        .hero-feature {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }

        .hero-feature-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-bottom: 8px;
        }

        .hero-feature-text {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
        }

        /* Main Layout */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .input-section {
            display: flex;
            flex-direction: column;
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

        /* Cover Letter Styles */
        .cover-letter-content {
            background: var(--bg-tertiary);
            padding: 24px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            line-height: 1.8;
            font-size: 15px;
            color: var(--text-primary);
            white-space: pre-wrap;
            margin-top: 16px;
        }

        .loading {
            display: none;
            padding: 20px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            margin-top: 16px;
        }

        .loading-steps {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .loading-step {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            transition: all 0.3s ease;
        }

        .loading-step.active {
            background: rgba(91, 140, 255, 0.1);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
        }

        .loading-step.completed {
            background: rgba(24, 199, 156, 0.1);
            border-color: var(--accent-success);
            color: var(--accent-success);
        }

        .loading-step-icon {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
        }

        .loading-step-text {
            flex: 1;
            font-size: 14px;
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

        .alert-warning {
            background: rgba(251, 191, 36, 0.15);
            border: 2px solid rgba(251, 191, 36, 0.4);
            color: #fbbf24;
            padding: 20px 24px;
            border-radius: var(--radius-md);
            margin-bottom: 24px;
            font-size: 15px;
            font-weight: 600;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            box-shadow: 0 4px 12px rgba(251, 191, 36, 0.1);
        }

        .alert-warning-icon {
            font-size: 24px;
            flex-shrink: 0;
        }

        .alert-warning-content {
            flex: 1;
            line-height: 1.6;
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

        <!-- Hero Section -->
        <div class="hero-section">
            <h1 class="hero-title">AI-Powered Career Matching</h1>
            <p class="hero-subtitle">
                Get instant, comprehensive analysis of your résumé against any job description. 
                Receive personalized course recommendations and project ideas to bridge skill gaps and advance your career.
            </p>
            <div class="hero-features">
                <div class="hero-feature">
                    <div class="hero-feature-icon">📊</div>
                    <div class="hero-feature-text">Skill Analysis</div>
                </div>
                <div class="hero-feature">
                    <div class="hero-feature-icon">📚</div>
                    <div class="hero-feature-text">Course Recommendations</div>
                </div>
                <div class="hero-feature">
                    <div class="hero-feature-icon">🚀</div>
                    <div class="hero-feature-text">Project Ideas</div>
                </div>
                <div class="hero-feature">
                    <div class="hero-feature-icon">🎯</div>
                    <div class="hero-feature-text">Gap Analysis</div>
                </div>
            </div>
        </div>

        <div class="main-layout">
            <!-- Input Section -->
            <div class="input-section">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Upload Your Résumé</div>
                    </div>
                    <div class="card-body">
                        <form id="matchForm" enctype="multipart/form-data">
                            <div class="form-group">
                                <label for="resume">Résumé File (PDF)</label>
                                <input type="file" id="resume" name="resume" accept=".pdf" required>
                            </div>
                            <div class="form-group">
                                <label for="job_description">Job Description</label>
                                <textarea id="job_description" name="job_description" 
                                          placeholder="Paste the complete job description here..." required></textarea>
                            </div>
                            <button type="submit" id="submitBtn" class="btn-primary">Analyze Match</button>
                        </form>
                        <div class="loading" id="loading">
                        <div class="loading-steps">
                            <div class="loading-step" id="step-1">
                                <div class="loading-step-icon">⏳</div>
                                <div class="loading-step-text">Step 1: Extracting skills from resume...</div>
                            </div>
                            <div class="loading-step" id="step-2">
                                <div class="loading-step-icon">⏳</div>
                                <div class="loading-step-text">Step 2: Extracting skills from job description...</div>
                            </div>
                            <div class="loading-step" id="step-3">
                                <div class="loading-step-icon">⏳</div>
                                <div class="loading-step-text">Step 3: Computing skills match scores...</div>
                            </div>
                            <div class="loading-step" id="step-4">
                                <div class="loading-step-icon">⏳</div>
                                <div class="loading-step-text">Step 4: Generating course recommendations...</div>
                            </div>
                            <div class="loading-step" id="step-5">
                                <div class="loading-step-icon">⏳</div>
                                <div class="loading-step-text">Step 5: Generating project recommendations...</div>
                            </div>
                        </div>
                    </div>
                    </div>
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
            
            // Reset all steps
            for (let i = 1; i <= 5; i++) {
                const step = document.getElementById(`step-${i}`);
                step.className = 'loading-step';
                step.querySelector('.loading-step-icon').textContent = '⏳';
            }
            
            // Start showing progress
            let currentStep = 0;
            const steps = [
                'Step 1: Extracting skills from resume...',
                'Step 2: Extracting skills from job description...',
                'Step 3: Computing skills match scores...',
                'Step 4: Generating course recommendations...',
                'Step 5: Generating project recommendations...'
            ];
            
            const updateStep = (stepIndex) => {
                // Mark previous steps as completed
                for (let i = 0; i < stepIndex; i++) {
                    const step = document.getElementById(`step-${i + 1}`);
                    step.className = 'loading-step completed';
                    step.querySelector('.loading-step-icon').textContent = '✅';
                }
                // Mark current step as active
                if (stepIndex < 5) {
                    const step = document.getElementById(`step-${stepIndex + 1}`);
                    step.className = 'loading-step active';
                    step.querySelector('.loading-step-icon').textContent = '🔄';
                }
            };
            
            // Simulate progress updates (since we can't get real-time updates from the API)
            const progressInterval = setInterval(() => {
                if (currentStep < 5) {
                    updateStep(currentStep);
                    currentStep++;
                } else {
                    clearInterval(progressInterval);
                }
            }, 2000); // Update every 2 seconds
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(progressInterval);
                // Mark all steps as completed
                for (let i = 1; i <= 5; i++) {
                    const step = document.getElementById(`step-${i}`);
                    step.className = 'loading-step completed';
                    step.querySelector('.loading-step-icon').textContent = '✅';
                }
                
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
                    
                    // Grad Student Job Warning
                    if (data.is_grad_student_job) {
                        html += `
                            <div class="alert alert-warning">
                                <div class="alert-warning-icon">🎓</div>
                                <div class="alert-warning-content">
                                    <strong>Graduate Student Position Detected</strong><br>
                                    This job requires a Master's or PhD degree. You may not be qualified for this position based on education requirements. However, you may still take your shot if you want to apply.
                                </div>
                            </div>
                        `;
                    }
                    
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
                            // Display all paid courses (1 or 2)
                            data.course_recommendations.paid_courses.forEach((paid, index) => {
                                const courseNumber = data.course_recommendations.paid_courses.length > 1 ? ` ${index + 1}` : '';
                                const borderStyle = index < data.course_recommendations.paid_courses.length - 1 ? 
                                    'margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid var(--border-color);' : '';
                                html += `
                                    <div style="${borderStyle}">
                                        <h4 style="color: var(--accent-primary); margin-bottom: 12px;">💰 Paid Course${courseNumber}: ${paid.title || 'N/A'}</h4>
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
                            });
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
                                
                                // Generate unique ID for this project's outline
                                const projectId = `project-${track.replace(/[^a-zA-Z0-9]/g, '-')}-${idx}`;
                                
                                html += `
                                    <div style="margin-bottom: 24px;">
                                        <span class="project-badge ${badgeClass}">${badgeText}</span>
                                        <div class="content-card project-card ${cardClass}">
                                            <h4>${project.title || 'Untitled Project'}</h4>
                                            <div class="detail"><strong>Difficulty:</strong> ${project.difficulty || 'N/A'}</div>
                                            <div class="detail"><strong>Estimated Time:</strong> ${project.estimated_time || 'N/A'}</div>
                                            ${project.description ? `<div class="description"><strong>Description:</strong><br>${project.description}</div>` : ''}
                                            ${project.tech_stack && project.tech_stack.length > 0 ? 
                                                `<div class="detail"><strong>Tech Stack:</strong> <ul><li>${project.tech_stack.join('</li><li>')}</li></ul></div>` : ''}
                                            ${project.key_features && project.key_features.length > 0 ? 
                                                `<div class="detail"><strong>Key Features:</strong> <ul><li>${project.key_features.join('</li><li>')}</li></ul></div>` : ''}
                                            ${project.skills_demonstrated && project.skills_demonstrated.length > 0 ? 
                                                `<div class="detail"><strong>Skills Demonstrated:</strong> <ul><li>${project.skills_demonstrated.join('</li><li>')}</li></ul></div>` : ''}
                                            ${project.technologies && project.technologies.length > 0 ? 
                                                `<div class="detail"><strong>Technologies:</strong> <ul><li>${project.technologies.join('</li><li>')}</li></ul></div>` : ''}
                                            ${project.project_outline ? 
                                                `<div class="detail">
                                                    <strong>Project Outline:</strong> 
                                                    <span id="${projectId}-outline" style="cursor: pointer; color: var(--accent-primary); text-decoration: underline;" onclick="toggleProjectPhases('${projectId}')">
                                                        ${project.project_outline}
                                                    </span>
                                                    <div id="${projectId}-phases" style="display: none; margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 6px; border-left: 3px solid var(--accent-primary);">
                                                        <strong style="display: block; margin-bottom: 8px;">Implementation Phases:</strong>
                                                        ${project.implementation_phases && project.implementation_phases.length > 0 ? 
                                                            project.implementation_phases.map((phase, phaseIdx) => {
                                                                const phaseName = typeof phase === 'object' ? phase.phase : phase;
                                                                const phaseDetails = typeof phase === 'object' ? phase.details : '';
                                                                return `
                                                                    <div style="margin-bottom: 12px;">
                                                                        <strong style="color: var(--accent-primary);">${phaseName || `Phase ${phaseIdx + 1}`}</strong>
                                                                        ${phaseDetails ? `<div style="margin-top: 4px; margin-left: 16px; color: var(--text-secondary);">${phaseDetails}</div>` : ''}
                                                                    </div>
                                                                `;
                                                            }).join('') : 
                                                            '<div style="color: var(--text-secondary);">No implementation phases available.</div>'
                                                        }
                                                    </div>
                                                </div>` : ''}
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
        
        function toggleProjectPhases(projectId) {
            const phasesDiv = document.getElementById(projectId + '-phases');
            const outlineSpan = document.getElementById(projectId + '-outline');
            if (phasesDiv) {
                if (phasesDiv.style.display === 'none') {
                    phasesDiv.style.display = 'block';
                    if (outlineSpan) {
                        outlineSpan.style.fontWeight = 'bold';
                    }
                } else {
                    phasesDiv.style.display = 'none';
                    if (outlineSpan) {
                        outlineSpan.style.fontWeight = 'normal';
                    }
                }
            }
        }
        
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the homepage with two tabs."""
    return templates.TemplateResponse("index.html", {"request": request})


async def analyze_with_progress(resume: UploadFile, job_text: str):
    """
    Analyze resume and job description match with progress updates.
    Yields progress messages and final result.
    """
    temp_path = None
    try:
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid file type. Only PDF files are allowed.'})}\n\n"
            return
        
        if not job_text.strip():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Job description is required'})}\n\n"
            return
        
        # Progress: Processing PDF
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing PDF resume...'})}\n\n"
        await asyncio.sleep(0.1)  # Small delay for UI update
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"resume_{os.getpid()}_{resume.filename}")
        
        with open(temp_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        # Convert PDF to text
        converter = PDFToTextConverter(temp_path)
        if not converter.convert():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to extract text from PDF'})}\n\n"
            return
        
        resume_text = converter.cleaned_text
        if not resume_text:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No text extracted from PDF. The PDF might be image-based or corrupted.'})}\n\n"
            return
        
        # Store progress messages (thread-safe list)
        progress_list = []
        progress_lock = threading.Lock()
        error_occurred = threading.Event()
        error_message = [None]  # Use list to allow modification from nested function
        
        def progress_callback(message: str):
            """Callback that stores progress (called from executor thread)"""
            with progress_lock:
                progress_list.append(message)
        
        # Start report generation in executor
        loop = asyncio.get_event_loop()
        
        def run_report():
            try:
                return generate_report(
                    resume_text=resume_text,
                    job_description_text=job_text,
                    role_label="Target Role",
                    progress_callback=progress_callback
                )
            except Exception as e:
                error_message[0] = str(e)
                error_occurred.set()
                raise
        
        report_task = loop.run_in_executor(None, run_report)
        
        # Poll for progress messages while waiting for report
        last_progress_count = 0
        emitted_messages = set()
        
        while not report_task.done():
            # Check if an error occurred
            if error_occurred.is_set():
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error generating report: {error_message[0]}'})}\n\n"
                return
            
            # Check for new progress messages
            with progress_lock:
                current_count = len(progress_list)
                if current_count > last_progress_count:
                    # Emit new progress messages
                    for i in range(last_progress_count, current_count):
                        if i < len(progress_list):
                            msg = progress_list[i]
                            if msg not in emitted_messages:
                                yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
                                emitted_messages.add(msg)
                    last_progress_count = current_count
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.3)
        
        # Check for errors after task completion
        if error_occurred.is_set():
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error generating report: {error_message[0]}'})}\n\n"
            return
        
        # Get final result
        try:
            report_result = await report_task
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error generating report: {str(e)}'})}\n\n"
            return
        
        # Emit any remaining progress messages
        with progress_lock:
            for i in range(last_progress_count, len(progress_list)):
                msg = progress_list[i]
                if msg not in emitted_messages:
                    yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
                    emitted_messages.add(msg)
        
        # Send final result
        yield f"data: {json.dumps({'type': 'complete', 'data': report_result})}\n\n"
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        yield f"data: {json.dumps({'type': 'error', 'message': f'Internal server error: {str(e)}', 'trace': error_trace})}\n\n"
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_text: str = Form(..., description="Job description text")
):
    """
    Analyze resume and job description match with streaming progress updates.
    
    - **resume**: PDF file containing the resume
    - **job_text**: Text description of the job posting
    
    Returns a streaming response with progress updates and final report.
    """
    return StreamingResponse(
        analyze_with_progress(resume, job_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def cover_letter_with_progress(resume: UploadFile, job_text: str, template: Optional[UploadFile]):
    """
    Generate cover letter with progress updates.
    Yields progress messages and final result.
    """
    temp_resume_path = None
    temp_template_path = None
    try:
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid file type. Only PDF files are allowed.'})}\n\n"
            return
        
        if not job_text.strip():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Job description is required'})}\n\n"
            return
        
        # Progress: Processing PDF
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing PDF resume...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Save uploaded resume file temporarily
        temp_dir = tempfile.gettempdir()
        temp_resume_path = os.path.join(temp_dir, f"resume_{os.getpid()}_{resume.filename}")
        
        with open(temp_resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        # Convert PDF to text
        converter = PDFToTextConverter(temp_resume_path)
        if not converter.convert():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to extract text from PDF'})}\n\n"
            return
        
        resume_text = converter.cleaned_text
        if not resume_text:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No text extracted from PDF. The PDF might be image-based or corrupted.'})}\n\n"
            return
        
        # Process template if provided
        template_text = None
        if template is not None:
            try:
                if hasattr(template, 'filename') and template.filename and template.filename.strip():
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Loading template file...'})}\n\n"
                    await asyncio.sleep(0.1)
                    temp_template_path = os.path.join(temp_dir, f"template_{os.getpid()}_{template.filename}")
                    with open(temp_template_path, "wb") as f:
                        content = await template.read()
                        f.write(content)
                    # Extract text from template file (supports .txt, .docx, .pdf)
                    template_text = extract_text_from_template_file(temp_template_path, template.filename)
            except Exception as e:
                error_msg = f"Failed to process template file: {str(e)}"
                print(f"Warning: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                template_text = None
        
        # Progress updates for cover letter generation
        steps = [
            'Extracting personal information from resume...',
            'Extracting company information from job description...',
            'Extracting skills and projects...',
            'Drafting cover letter content...'
        ]
        
        for step in steps:
            yield f"data: {json.dumps({'type': 'progress', 'message': step})}\n\n"
            await asyncio.sleep(0.2)
        
        # Generate cover letter
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generate_cover_letter_from_text(
                resume_text=resume_text,
                job_text=job_text,
                template_text=template_text
            )
        )
        
        # Send final result
        yield f"data: {json.dumps({'type': 'complete', 'data': result})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Internal server error: {str(e)}'})}\n\n"
    finally:
        for temp_path in [temp_resume_path, temp_template_path]:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

@app.post("/cover-letter")
async def cover_letter(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_text: str = Form(..., description="Job description text"),
    template: Optional[UploadFile] = File(None, description="Optional cover letter template file")
):
    """
    Generate a tailored cover letter with streaming progress updates.
    
    - **resume**: PDF file containing the resume
    - **job_text**: Text description of the job posting
    - **template**: Optional template file (text format)
    
    Returns a streaming response with progress updates and final cover letter.
    """
    return StreamingResponse(
        cover_letter_with_progress(resume, job_text, template),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/analyze-sync")
async def analyze_sync(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_text: str = Form(..., description="Job description text")
):
    """
    Synchronous analyze endpoint (fallback for environments where SSE doesn't work).
    Returns JSON response directly without streaming.
    Includes request deduplication to prevent duplicate processing.
    """
    temp_path = None
    try:
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail='Invalid file type. Only PDF files are allowed.')
        
        if not job_text.strip():
            raise HTTPException(status_code=400, detail='Job description is required')
        
        # Create request hash for deduplication (based on file content + job text)
        content = await resume.read()
        request_hash = hashlib.md5(
            content + job_text.encode('utf-8')
        ).hexdigest()
        
        # Check cache for duplicate request
        with _cache_lock:
            current_time = time.time()
            if request_hash in _request_cache:
                cached_result, cache_time = _request_cache[request_hash]
                if current_time - cache_time < _cache_ttl:
                    print(f"Debug: Returning cached result for request {request_hash[:8]}...")
                    return JSONResponse(content=cached_result)
                else:
                    # Cache expired, remove it
                    del _request_cache[request_hash]
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"resume_{os.getpid()}_{resume.filename}")
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Convert PDF to text
        converter = PDFToTextConverter(temp_path)
        if not converter.convert():
            raise HTTPException(status_code=400, detail='Failed to extract text from PDF')
        
        resume_text = converter.cleaned_text
        if not resume_text:
            raise HTTPException(status_code=400, detail='No text extracted from PDF. The PDF might be image-based or corrupted.')
        
        # Generate report synchronously
        loop = asyncio.get_event_loop()
        report_result = await loop.run_in_executor(
            None,
            lambda: generate_report(
                resume_text=resume_text,
                job_description_text=job_text,
                role_label="Target Role",
                progress_callback=None
            )
        )
        
        # Cache the result
        with _cache_lock:
            _request_cache[request_hash] = (report_result, time.time())
            # Clean up old cache entries (keep only last 10)
            if len(_request_cache) > 10:
                # Remove oldest entries
                sorted_cache = sorted(_request_cache.items(), key=lambda x: x[1][1])
                for key, _ in sorted_cache[:-10]:
                    del _request_cache[key]
        
        return JSONResponse(content=report_result)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in analyze_sync: {error_trace}")
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/cover-letter-sync")
async def cover_letter_sync(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_text: str = Form(..., description="Job description text"),
    template: Optional[UploadFile] = File(None, description="Optional cover letter template file")
):
    """
    Synchronous cover letter endpoint (fallback for environments where SSE doesn't work).
    Returns JSON response directly without streaming.
    """
    temp_resume_path = None
    temp_template_path = None
    try:
        # Validate file type
        if not resume.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail='Invalid file type. Only PDF files are allowed.')
        
        if not job_text.strip():
            raise HTTPException(status_code=400, detail='Job description is required')
        
        # Save uploaded resume file temporarily
        temp_dir = tempfile.gettempdir()
        temp_resume_path = os.path.join(temp_dir, f"resume_{os.getpid()}_{resume.filename}")
        
        with open(temp_resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        # Convert PDF to text
        converter = PDFToTextConverter(temp_resume_path)
        if not converter.convert():
            raise HTTPException(status_code=400, detail='Failed to extract text from PDF')
        
        resume_text = converter.cleaned_text
        if not resume_text:
            raise HTTPException(status_code=400, detail='No text extracted from PDF. The PDF might be image-based or corrupted.')
        
        # Process template if provided
        template_text = None
        if template is not None:
            try:
                if hasattr(template, 'filename') and template.filename and template.filename.strip():
                    temp_template_path = os.path.join(temp_dir, f"template_{os.getpid()}_{template.filename}")
                    with open(temp_template_path, "wb") as f:
                        content = await template.read()
                        f.write(content)
                    # Extract text from template file (supports .txt, .docx, .pdf)
                    template_text = extract_text_from_template_file(temp_template_path, template.filename)
            except Exception as e:
                error_msg = f"Failed to process template file: {str(e)}"
                print(f"Warning: {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        
        # Generate cover letter synchronously
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generate_cover_letter_from_text(
                resume_text=resume_text,
                job_text=job_text,
                template_text=template_text
            )
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in cover_letter_sync: {error_trace}")
        raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
    finally:
        for temp_path in [temp_resume_path, temp_template_path]:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Resume-Job Match Analyzer"}


if __name__ == '__main__':
    import uvicorn
    # Get port and host from environment variables (for deployment compatibility)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # For local development, show localhost in the message (0.0.0.0 is not accessible in browser)
    display_host = "localhost" if host == "0.0.0.0" else host
    print(f"🚀 FastAPI app starting on http://{display_host}:{port}")
    print(f"📖 API documentation available at http://{display_host}:{port}/docs")
    print(f"   (Server binding to {host}:{port})")
    uvicorn.run(app, host=host, port=port)
