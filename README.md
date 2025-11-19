# 🚀 skillbridge.AI

<div align="center">

**Your AI-Powered Career Companion**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Online-brightgreen)](https://level-up-llm-skill-analyzer.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
- [License](#license)

---

## 🎯 Overview

**skillbridge.AI** is an intelligent career development platform that helps students and job seekers identify skill gaps between their résumé and target job positions. Using advanced Large Language Models (LLMs), the platform provides personalized course recommendations, hands-on project ideas, and AI-generated cover letters to help bridge these gaps and land dream internships or new grad positions.

### Key Objectives

- **Skill Gap Analysis**: Automatically identify missing skills required for target positions
- **Personalized Learning**: Recommend relevant courses from Udemy and Coursera
- **Project-Based Learning**: Generate actionable project ideas to build missing skills
- **Cover Letter Generation**: Create tailored cover letters using AI

---

## 🎥 Demo

<div align="center">

### Watch the Demo Video

[![Demo Video](https://img.shields.io/badge/▶️-Watch%20Demo%20Video-red)](https://drive.google.com/file/d/1rwbXLnQzjT6PDIEMzjZcBVmqD1B0OlYA/view?usp=drive_link)

**Or visit the live application**: [https://level-up-llm-skill-analyzer.onrender.com/](https://level-up-llm-skill-analyzer.onrender.com/)

</div>

---

## ✨ Features

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

---

## 🛠️ Tech Stack

### Backend

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- **Language**: Python 3.8+
- **LLM**: OpenAI GPT Models (via OpenAI API)
- **Database**: MongoDB (PyMongo) - Course data storage
- **PDF Processing**: PyMuPDF, PyPDF2, pdfminer.six
- **Document Support**: python-docx (Word documents)

### Frontend

- **Templates**: Jinja2
- **Styling**: Custom CSS with modern design
- **JavaScript**: Vanilla JS with Server-Sent Events (SSE) for real-time updates

### Infrastructure

- **Deployment**: [Render](https://render.com/)
- **Database**: MongoDB Atlas

---

## 🏗️ System Architecture

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

## 🚀 Usage

### Web Interface

Visit the [live application](https://level-up-llm-skill-analyzer.onrender.com/) and:

1. **Skill Gap Analyzer Tab**:
   - Upload your PDF résumé
   - Paste the job description
   - Click "Analyze Match"
   - View comprehensive skill gap analysis with course and project recommendations

2. **Cover Letter Generator Tab**:
   - Upload your PDF résumé
   - Paste the job description
   - Optionally upload a cover letter template
   - Click "Generate Cover Letter"
   - Copy the generated cover letter

### API Endpoints

#### Skill Gap Analysis

**POST** `/analyze` (SSE Streaming)
```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/analyze" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here"
```

**POST** `/analyze-sync` (Synchronous)
```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/analyze-sync" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here"
```

#### Cover Letter Generation

**POST** `/cover-letter` (SSE Streaming)
```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/cover-letter" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here" \
  -F "template=@template.txt"  # Optional
```

**POST** `/cover-letter-sync` (Synchronous)
```bash
curl -X POST "https://level-up-llm-skill-analyzer.onrender.com/cover-letter-sync" \
  -F "resume=@your_resume.pdf" \
  -F "job_text=Your job description here"
```

---

## 📚 API Documentation

### Response Format

#### Skill Gap Analysis Response

```json
{
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
    "free_courses": [...],
    "paid_courses": [...],
    "skill_coverage": {...},
    "coverage_percentage": 75
  },
  "project_recommendations": {
    "MLOps (Marketing)": [
      {
        "title": "Project Name",
        "description": "...",
        "tech_stack": [...],
        "implementation_phases": [...]
      }
    ]
  },
  "is_grad_student_job": false
}
```

#### Cover Letter Response

```json
{
  "cover_letter": "Generated cover letter text here..."
}
```

---

## 📁 Project Structure

```
level-up-llm-skill-analyzer/
├── app_fastapi.py              # Main FastAPI application
├── extract_skills.py            # Résumé skill extraction
├── extract_job_skills.py       # Job description skill extraction
├── score_skills_match.py        # Skill matching and scoring
├── recommend_courses.py         # Course recommendation engine
├── recommend_projects.py        # Project recommendation generator
├── generate_report.py           # Report generation orchestrator
├── generate_cover_letter.py     # Cover letter generator
├── pdf_resume_parser.py         # PDF text extraction
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── CTP_template.txt            # Cover letter template example
└── templates/
    ├── index.html               # Main UI template
    ├── skill_analyzer.html      # Analysis form template
    └── cover_letter.html        # Cover letter form template
```

---

## 👥 Authors

- **Ahmed Ali** - [GitHub](https://github.com/AhmedKamal-41)
- **Surjo Barua** - [GitHub](https://github.com/Surfs101)
- **Jiayu Ouyang** - [GitHub](https://github.com/3ouyang3)
- **Ibnan Hasan**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for students and job seekers**

[⭐ Star this repo](https://github.com/AhmedKamal-41/level-up-llm-skill-analyzer) | [🌐 Live Demo](https://level-up-llm-skill-analyzer.onrender.com/)

</div>
