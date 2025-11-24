# 🚀 skillbridge.AI

<div align="center">

**Your AI-Powered Career Companion**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Online-brightgreen)](https://level-up-llm-skill-analyzer.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)](https://openai.com/)
[🌐 Live Website](https://level-up-llm-skill-analyzer.onrender.com/)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Demo](#demo)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Authors](#authors)

---

## 🎯 Overview <a id="overview"></a>

**skillbridge.AI** is an intelligent career development platform that helps students and job seekers identify skill gaps between their résumé and target job positions. Using advanced Large Language Models (LLMs), the platform provides personalized course recommendations, hands-on project ideas, and AI-generated cover letters to help bridge these gaps and land dream internships or new grad positions.

### Key Objectives

- **Skill Gap Analysis**: Automatically identify missing skills required for target positions
- **Personalized Learning**: Recommend relevant courses from Udemy and Coursera
- **Project-Based Learning**: Generate actionable project ideas to build missing skills
- **Cover Letter Generation**: Create tailored cover letters using AI

---

## 🎥 Demo <a id="demo"></a>

<div align="center">

### Watch the Demo Video

<a href="https://youtu.be/728sAVC96EI">
  <img src="https://img.youtube.com/vi/728sAVC96EI/maxresdefault.jpg" alt="skillbridge.AI Demo Video" style="width:100%;max-width:800px;border-radius:8px;">
</a>

<p><a href="https://youtu.be/728sAVC96EI">▶️ Watch on YouTube</a></p>

**Or visit the live application**: [https://level-up-llm-skill-analyzer.onrender.com/](https://level-up-llm-skill-analyzer.onrender.com/)

</div>

---

## ✨ Features <a id="features"></a>

### 🔍 Skill Gap Analyzer

- **Automated Skill Extraction**: Extracts skills from both résumé and job descriptions using LLM
- **Intelligent Matching**: Compares required vs. available skills with weighted scoring
- **Visual Analytics**: Displays match percentages, coverage statistics, and gap analysis
- **Skill Categorization**: Organizes skills into Programming Languages, Frameworks/Libraries, Tools/Platforms, and Soft Skills

### 📚 Course Recommendations

- **Multi-Platform Support**: Searches across Udemy and Coursera databases
- **Free & Paid Options**: Provides both free and paid course recommendations
- **Skill-Based Matching**: Matches courses to missing skills with deep search algorithms
- **Detailed Course Info**: Includes duration, difficulty, ratings, costs, and direct links

### 🛠️ Project Recommendations

- **Two-Track Approach**:
  - **Project 1**: Build with your current skills (immediate portfolio projects)
  - **Project 2**: Learn missing skills (projects that help you grow)
- **Comprehensive Details**: Includes tech stack, implementation phases, key features, and portfolio impact
- **Actionable Outlines**: Step-by-step project breakdowns with specific deliverables

### ✍️ AI Cover Letter Generator

- **Personalized Content**: Generates job-specific cover letters using your résumé
- **Template Support**: Accepts custom templates (.txt, .docx, .pdf)
- **Professional Formatting**: Creates ready-to-use cover letters
- **One-Click Copy**: Easy copy-to-clipboard functionality
- **Real-time Progress**: Live progress updates during generation

### ⚡ Performance Features

- **Request Caching**: Intelligent request deduplication to prevent duplicate processing (60-second TTL)
- **Streaming Responses**: Server-Sent Events (SSE) for real-time progress updates
- **Graduate Student Detection**: Automatically detects if a job requires graduate-level education
- **Multi-format Support**: Handles PDF, DOCX, and TXT files for templates

---

## 🛠️ Tech Stack <a id="tech-stack"></a>

### Frontend Technologies

- **HTML5** - Markup language for structuring web pages
- **CSS3** - Styling and modern design with custom responsive layouts
- **JavaScript (Vanilla JS)** - Client-side scripting for interactive UI
- **Jinja2** - Server-side templating engine for dynamic HTML generation
- **Server-Sent Events (SSE)** - Real-time streaming updates for progress tracking

### Backend Technologies

- **Python 3.8+** - Primary programming language
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI applications
- **python-multipart** - File upload handling

### AI & Machine Learning

- **OpenAI API** - GPT models for:
  - Skill extraction from résumés and job descriptions
  - Course and project recommendations
  - AI-powered cover letter generation
- **OpenAI Python SDK** - Official Python client for OpenAI API

### Database

- **MongoDB** - NoSQL database for storing course data
- **PyMongo** - MongoDB Python driver
- **MongoDB Atlas** - Cloud database hosting

### Document Processing

- **PDF Processing**:
  - **PyMuPDF (fitz)** - Fast and efficient PDF parsing
  - **PyPDF2** - PDF text extraction
  - **pdfminer.six** - Advanced PDF parsing and text extraction
- **OCR (Optical Character Recognition)**:
  - **pytesseract** - Text extraction from scanned documents
  - **Pillow (PIL)** - Image processing for OCR
- **Word Documents**:
  - **python-docx** - Microsoft Word (.docx) file processing

### Data Processing & Utilities

- **pandas** - Data manipulation and analysis for course data
- **chardet** - Character encoding detection
- **argparse** - Command-line argument parsing

### Development & Deployment

- **python-dotenv** - Environment variable management
- **Git & GitHub** - Version control and code repository
- **Render** - Cloud hosting platform for deployment

### Additional Features

- **Request Deduplication** - In-memory caching to prevent duplicate processing
- **Progress Callbacks** - Real-time progress tracking during long-running operations
- **Error Handling** - Comprehensive error handling with detailed error messages
- **File Validation** - Automatic file type validation and error reporting

---

## 🏗️ System Architecture <a id="system-architecture"></a>

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Web UI)                     │
│              HTML/CSS/JavaScript + Jinja2 Templates         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Server                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Resume     │  │  Job Skills  │  │   Scoring    │      │
│  │  Extraction  │  │  Extraction  │  │   Engine    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Course     │  │   Project    │  │   Cover      │      │
│  │ Recommender  │  │ Recommender  │  │   Letter     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────┬───────────────────┬───────────────────┬────────┘
            │                   │                   │
            ▼                   ▼                   ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │   OpenAI     │    │   MongoDB    │    │   PDF Parser │
    │     API      │    │   Database   │    │   Libraries  │
    └──────────────┘    └──────────────┘    └──────────────┘
```

### Data Flow

```
┌─────────────────────┐
│   Resume Text       │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│         │
│   Extract Skills    │
└─────────────────────┘
         │
         ▼
         │
         └─────────────────┐
                           │
┌─────────────────────┐    │
│   Job Text          │    │
└─────────────────────┘    │
         │                 │
         ▼                 │
┌─────────────────────┐    │
│                     │    │
│   Extract Skills    │    │
└─────────────────────┘    │
         │                 │
         ▼                 │    
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │                     │
         │   Match & Score     │
         └─────────────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ match_scores        │
         └─────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 │
┌─────────────────────┐    │
│                     │    │
│   Recommend         │    │
│   Courses           │    │
└─────────────────────┘    │
         │                 │
         ▼                 │   
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │                     │
         │   Recommend         │
         │   Projects          │
         └─────────────────────┘
                  │
                  │
                  ▼
         ┌─────────────────────┐
         │ final_report         │
         └─────────────────────┘
```

1. **Input**: User uploads PDF résumé and pastes job description
2. **Parsing**: PDF text extraction using multiple parsing methods
3. **Skill Extraction**: LLM extracts and categorizes skills from both documents
4. **Comparison**: Skills are compared to identify gaps
5. **Scoring**: Match scores calculated (overall, required, preferred)
6. **Recommendations**: 
   - Courses fetched from MongoDB based on missing skills
   - Projects generated using LLM
7. **Output**: Comprehensive report with all recommendations

---

## 🚀 Usage <a id="usage"></a>

### Web Interface

Visit the [live application](https://level-up-llm-skill-analyzer.onrender.com/) and:

1. **Skill Gap Analyzer Tab**:
   - Upload your PDF résumé
   - Paste the job description
   - Click "Analyze Match"
   - Watch real-time progress updates as the system processes your request
   - View comprehensive skill gap analysis with:
     - Overall match score and coverage statistics
     - Required and preferred skills breakdown
     - Course recommendations (free and paid options)
     - Project recommendations (build with current skills vs. learn missing skills)
     - Graduate student job detection warnings

2. **Cover Letter Generator Tab**:
   - Upload your PDF résumé
   - Paste the job description
   - Optionally upload a cover letter template (.txt, .docx, or .pdf)
   - Click "Generate Cover Letter"
   - Watch real-time progress updates during generation
   - Copy the generated cover letter with one click

### API Endpoints

#### Homepage

**GET** `/`
- Returns the main web interface with tabs for Skill Gap Analyzer and Cover Letter Generator

#### Skill Gap Analysis

**POST** `/analyze` (SSE Streaming)
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `resume` (file, required): PDF resume file
  - `job_text` (string, required): Job description text
- **Response**: Server-Sent Events stream with progress updates and final JSON result
- **Features**: Request caching, real-time progress tracking

```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/analyze" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here"
```

#### Cover Letter Generation

**POST** `/cover-letter` (SSE Streaming)
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `resume` (file, required): PDF resume file
  - `job_text` (string, required): Job description text
  - `template` (file, optional): Cover letter template (.txt, .docx, or .pdf)
- **Response**: Server-Sent Events stream with progress updates and final cover letter

```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/cover-letter" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here" \
  -F "template=@template.txt"  # Optional
```

#### Health Check

**GET** `/health`
- Returns service health status
- **Response**: `{"status": "healthy", "service": "Resume-Job Match Analyzer"}`

---

## 📚 API Documentation <a id="api-documentation"></a>

### Response Format

#### Skill Gap Analysis Response (SSE Stream)

The `/analyze` endpoint returns Server-Sent Events (SSE) with the following message types:

**Progress Messages:**
```json
{
  "type": "progress",
  "message": "Extracting skills from resume..."
}
```

**Complete Response:**
```json
{
  "type": "complete",
  "data": {
    "overall_score": {
      "weighted_score": 75.5,
      "total_skills": 20,
      "matched_skills": 15
    },
    "required_skills": {
      "total_count": 10,
      "covered_count": 8,
      "match_score": 80.0,
      "covered_skills": ["Python", "FastAPI", "MongoDB"],
      "missing_skills": ["Docker", "Kubernetes"]
    },
    "preferred_skills": {
      "total_count": 10,
      "covered_count": 7,
      "match_score": 70.0,
      "covered_skills": ["React", "TypeScript"],
      "missing_skills": ["AWS", "GraphQL", "Redis"]
    },
    "course_recommendations": {
      "free_courses": [
        {
          "title": "Course Title",
          "platform": "Udemy",
          "duration": "10 hours",
          "difficulty": "Intermediate",
          "cost": "Free",
          "link": "https://...",
          "skills_covered": ["Python", "FastAPI"],
          "description": "...",
          "why_efficient": "..."
        }
      ],
      "paid_courses": [
        {
          "title": "Course Title",
          "platform": "Coursera",
          "duration": "20 hours",
          "difficulty": "Advanced",
          "cost": "$49.99",
          "link": "https://...",
          "skills_covered": ["Docker", "Kubernetes"],
          "description": "...",
          "why_efficient": "..."
        }
      ],
      "skill_coverage": {...},
      "coverage_percentage": 75
    },
    "project_recommendations": {
      "Track Name": [
        {
          "title": "Project Name",
          "description": "...",
          "difficulty": "Intermediate",
          "estimated_time": "2-3 weeks",
          "tech_stack": ["Python", "FastAPI", "MongoDB"],
          "key_features": ["Feature 1", "Feature 2"],
          "skills_demonstrated": ["Skill 1", "Skill 2"],
          "technologies": ["Tech 1", "Tech 2"],
          "project_outline": "High-level overview",
          "implementation_phases": [
            {
              "phase": "Phase 1: Setup",
              "details": "Detailed steps..."
            }
          ],
          "portfolio_impact": "...",
          "bonus_challenges": ["Challenge 1", "Challenge 2"]
        }
      ]
    },
    "is_grad_student_job": false
  }
}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "Error description here"
}
```

#### Cover Letter Response (SSE Stream)

The `/cover-letter` endpoint returns Server-Sent Events (SSE) with similar structure:

**Progress Messages:**
```json
{
  "type": "progress",
  "message": "Extracting personal information from resume..."
}
```

**Complete Response:**
```json
{
  "type": "complete",
  "data": {
    "cover_letter": "Generated cover letter text here..."
  }
}
```

### Interactive API Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI**: Available at `/docs` when running locally
- **ReDoc**: Available at `/redoc` when running locally

---

## 📁 Project Structure <a id="project-structure"></a>

```
level-up-llm-skill-analyzer/
├── app_fastapi.py              # Main FastAPI application with SSE streaming
├── extract_skills.py            # Résumé skill extraction using LLM
├── extract_job_skills.py        # Job description skill extraction using LLM
├── score_skills_match.py        # Skill matching and scoring engine
├── recommend_courses.py         # Course recommendation engine (MongoDB integration)
├── recommend_projects.py        # Project recommendation generator using LLM
├── generate_report.py           # Report generation orchestrator
├── generate_cover_letter.py     # AI-powered cover letter generator
├── pdf_resume_parser.py         # Multi-method PDF text extraction (PyMuPDF, PyPDF2, pdfminer)
├── skill_normalization.py      # Skill normalization and canonicalization
├── check_setup.py               # Setup verification script
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── CTP_template.txt            # Cover letter template example
├── scripts/
│   └── load_courses_to_mongo.py # Script to load course data into MongoDB
└── templates/
    ├── index.html               # Main UI template with tabs
    ├── skill_analyzer.html      # Skill analysis form template
    └── cover_letter.html        # Cover letter form template
```

---

## 👥 Authors <a id="authors"></a>

- **Ahmed Ali** - [GitHub](https://github.com/AhmedKamal-41)
- **Surjo Barua** - [GitHub](https://github.com/Surfs101)
- **Jiayu Ouyang** - [GitHub](https://github.com/3ouyang3)
- **Ibnan Hasan**

---

<div align="center">

**Made with ❤️ for students and job seekers**

[⭐ Star this repo](https://github.com/AhmedKamal-41/level-up-llm-skill-analyzer) | [🌐 Live Demo](https://level-up-llm-skill-analyzer.onrender.com/)

</div>
