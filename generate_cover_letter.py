"""
generate_cover_letter.py
Phase 2: Tailored cover-letter generator

What it does
------------
1) Gets clean resume text (if a PDF is provided, it uses pdf_resume_parser.PDFToTextConverter).
2) Extracts **skills** by reusing YOUR EXACT pipeline in `extract_skills.py`
   (we invoke it as a subprocess on a temp .txt to guarantee identical behavior).
3) Extracts **projects/experiences** from the resume via an OpenAI JSON call.
4) Loads a user-provided plaintext **template** (fallback to a built-in skeleton).
5) Drafts a **cover letter** aligned to the job description, constrained to ONLY info
   present in the resume (skills/projects) and formatted into the template.
6) Writes outputs to disk and prints a compact JSON summary to stdout.

Usage
-----
python generate_cover_letter.py \
  --resume /path/to/resume.pdf \
  --job /path/to/job_description.txt \
  --template /path/to/template.txt \
  --out cover_letter.txt

Outputs
-------
- cover_letter.txt              (final letter)
- cover_letter_meta.json        (skills_used, projects_referenced, meta)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from dotenv import load_dotenv
from openai import OpenAI

# --- ENV / CLIENT ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY missing in environment.")
    sys.exit(1)
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Helpers ---
def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def _extract_paragraphs(text: str) -> List[str]:
    """
    Extract paragraphs from text, handling both line-break and period-separated formats.
    
    First tries splitting by double newlines. If that doesn't yield good results,
    falls back to splitting by periods followed by spaces/capital letters.
    
    Args:
        text: Input text to extract paragraphs from
    
    Returns:
        List of paragraph strings
    """
    # First, try splitting by double newlines (most common format)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    # If we got good results (multiple paragraphs of reasonable length), use them
    if len(paragraphs) >= 2:
        # Check if paragraphs are substantial (not just single sentences)
        substantial_paras = [p for p in paragraphs if len(p) > 50]
        if len(substantial_paras) >= 2:
            return paragraphs
    
    # If splitting by newlines didn't work well, try splitting by periods
    # Look for patterns like ". " followed by a capital letter (new paragraph)
    # or periods at the end of lines
    # Pattern: period followed by space and capital letter (likely new paragraph)
    # Also handle cases where period is at end of line
    para_pattern = r'\.\s+(?=[A-Z][a-z])|\.\n+|\.\r\n+'
    
    # Split by the pattern
    potential_paras = re.split(para_pattern, text)
    
    # Clean up and filter
    cleaned_paras = []
    for para in potential_paras:
        para = para.strip()
        # Only keep substantial paragraphs (more than just a few words)
        if para and len(para) > 30:
            cleaned_paras.append(para)
    
    # If we got better results with period splitting, use those
    if len(cleaned_paras) >= 2:
        return cleaned_paras
    
    # Fallback: if all else fails, treat the whole text as one paragraph
    # or split by single newlines as last resort
    if text.strip():
        single_line_paras = [p.strip() for p in text.split("\n") if p.strip() and len(p.strip()) > 30]
        if single_line_paras:
            return single_line_paras
        return [text.strip()]
    
    return []

def load_template_file(path: Path) -> str:
    """
    Load a user-provided template / old cover letter file and return its plain-text content.
    Supports .txt/.md, .pdf, and .doc/.docx. Falls back to raw text for unknown extensions.
    """
    ext = path.suffix.lower()
    
    # Simple text formats
    if ext in {".txt", ".md"}:
        return _read_text_file(path)
    
    # PDF → use the same converter we already use for resumes
    if ext == ".pdf":
        try:
            from pdf_resume_parser import PDFToTextConverter
        except ImportError as e:
            raise RuntimeError(
                "pdf_resume_parser.PDFToTextConverter is required to use PDF as a template."
            ) from e
        
        conv = PDFToTextConverter(str(path))
        ok = conv.convert()
        if not ok:
            raise RuntimeError(f"Failed to convert template PDF to text: {path}")
        # use cleaned_text just like for resumes
        return conv.cleaned_text
    
    # DOC/DOCX → use python-docx
    if ext in {".doc", ".docx"}:
        try:
            from docx import Document
        except ImportError as e:
            raise RuntimeError(
                "python-docx is required to use .doc/.docx files as templates."
            ) from e
        
        doc = Document(str(path))
        # join paragraphs with blank lines so paragraph splitting works later
        return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    
    # Fallback: read as text anyway (best-effort)
    return _read_text_file(path)

def _load_template(template_path: Optional[Path]) -> str:
    if template_path and template_path.exists():
        return _read_text_file(template_path)
    # Use CTP_template.txt as default template
    default_template_path = Path(__file__).parent / "CTP_template.txt"
    if default_template_path.exists():
        return _read_text_file(default_template_path)
    # Fallback to very light skeleton if CTP_template.txt doesn't exist
    return (
        "Dear Hiring Manager,\n\n"
        "<<BODY>>\n\n"
        "Sincerely,\n"
        "<Your Name>\n"
    )

def _inject_body_into_template(template: str, body: str) -> str:
    # Support several common markers; otherwise append to end.
    for marker in ("<<BODY>>", "{{BODY}}", "[[BODY]]", "[BODY]"):
        if marker in template:
            return template.replace(marker, body.strip())
    
    # For CTP template format: replace content between "Dear Hiring Manager:" and "Thank you for your time"
    # Look for the pattern: "Dear Hiring Manager:" ... existing paragraphs ... "Thank you for your time"
    dear_match = re.search(r"Dear Hiring Manager[:\s]*\n+", template, re.IGNORECASE)
    thank_match = re.search(r"\n+Thank you for your time and consideration", template, re.IGNORECASE)
    
    if dear_match and thank_match:
        # Replace everything between "Dear Hiring Manager:" and "Thank you for your time"
        start_idx = dear_match.end()
        end_idx = thank_match.start()
        return template[:start_idx] + "\n\n" + body.strip() + "\n\n" + template[end_idx:]
    
    # Fallback: If no marker, append the body before the closing sign-off if we find one.
    m = re.search(r"\n\s*(Sincerely|Regards|Best),", template, re.IGNORECASE)
    if m:
        idx = m.start()
        return template[:idx].rstrip() + "\n\n" + body.strip() + "\n\n" + template[idx:]
    return template.rstrip() + "\n\n" + body.strip() + "\n"

def _safe_unique(seq: List[str], limit: Optional[int] = None) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        k = x.strip()
        if not k or k.lower() in seen:
            continue
        seen.add(k.lower())
        out.append(k)
        if limit and len(out) >= limit:
            break
    return out

# --- 1) Resume text loader (with PDF support) ---
def load_resume_text(resume_path: Path) -> str:
    if resume_path.suffix.lower() == ".pdf":
        # Import lazily to keep this file standalone when PDF is not needed
        try:
            from pdf_resume_parser import PDFToTextConverter
        except Exception as e:
            print("❌ Could not import pdf_resume_parser.PDFToTextConverter:", e)
            sys.exit(1)
        conv = PDFToTextConverter(str(resume_path))
        if not conv.convert():
            raise RuntimeError(f"Failed to convert PDF: {resume_path}")
        return conv.cleaned_text
    else:
        return _read_text_file(resume_path)

# --- 2) Skills via extract_skills.py (subprocess to guarantee parity) ---
def extract_skills_with_script(resume_text: str) -> Dict[str, List[str]]:
    """
    Writes resume_text to a temp file and calls:
      python extract_skills.py <tempfile>
    Then returns the JSON's 'skills' dict with the 3 buckets.
    """
    script_path = Path(__file__).parent / "extract_skills.py"
    if not script_path.exists():
        print("❌ extract_skills.py not found next to generate_cover_letter.py")
        sys.exit(1)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix="_resume_cleaned.txt", encoding="utf-8") as tf:
        tf.write(resume_text)
        tmp_name = tf.name

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), tmp_name],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if proc.returncode != 0:
            raise RuntimeError(f"extract_skills.py failed with return code {proc.returncode}.\nSTDERR: {proc.stderr}")
        
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        
        # Try to parse JSON from stdout (should be clean JSON now)
        data = None
        try:
            # First, try parsing stdout directly as JSON
            data = json.loads(stdout)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON using regex (for backwards compatibility)
            json_match = re.search(r'\{[\s\S]*\}', stdout)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        # If parsing from stdout failed, try reading the output file directly
        if data is None:
            output_file = os.path.splitext(tmp_name)[0] + "_skills.json"
            if os.path.exists(output_file):
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    pass
        
        if data is None:
            raise RuntimeError(
                f"Could not parse skills JSON from extract_skills.py output.\n"
                f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
            )
        
        skills = data.get("skills", {})
        # Ensure schema presence
        for k in ("ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"):
            skills.setdefault(k, [])
        return skills
    finally:
        try:
            os.remove(tmp_name)
            # Also try to clean up the skills JSON file if it exists
            output_file = os.path.splitext(tmp_name)[0] + "_skills.json"
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError:
                    pass
        except OSError:
            pass

# --- 3) Extract personal information from resume ---
def extract_personal_info_from_resume(resume_text: str) -> Dict[str, Optional[str]]:
    """
    Extract personal information from resume text.
    Returns: {first_name, last_name, email, phone, address}
    """
    # First, try simple extraction from first lines
    lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
    
    # Extract name from first line (most common pattern)
    first_name = None
    last_name = None
    if lines:
        first_line = lines[0]
        # Check if first line looks like a name (2-4 words, no special characters)
        if first_line and len(first_line.split()) >= 2 and len(first_line.split()) <= 4:
            # Check if it doesn't contain typical non-name characters
            non_name_chars = ['@', '|', '•', ':', 'http', 'www', 'github', 'linkedin', 'email', 'phone', 'resume']
            if not any(char in first_line.lower() for char in non_name_chars):
                # Check if it's mostly letters (allowing spaces and hyphens)
                if re.match(r'^[A-Za-z]+(?:\s+[A-Za-z-]+)+$', first_line):
                    name_parts = first_line.split()
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
    
    # Extract email from any line
    email = None
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for line in lines[:5]:  # Check first 5 lines for email
        email_match = re.search(email_pattern, line)
        if email_match:
            email = email_match.group(0)
            break
    
    # Extract phone from any line
    phone = None
    phone_patterns = [
        r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
        r'\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
    ]
    for line in lines[:5]:  # Check first 5 lines for phone
        for pattern in phone_patterns:
            phone_match = re.search(pattern, line)
            if phone_match:
                phone = phone_match.group(0).strip()
                break
        if phone:
            break
    
    # Extract address (look for patterns like "City, State" or full addresses)
    address = None
    address_patterns = [
        r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)[,\s]+[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
        r'[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',  # City, State ZIP
        r'[A-Za-z\s]+,\s*[A-Z]{2}',  # City, State
    ]
    for line in lines[:10]:  # Check first 10 lines
        for pattern in address_patterns:
            addr_match = re.search(pattern, line)
            if addr_match:
                # Make sure it's not an email or URL
                if '@' not in line and 'http' not in line.lower():
                    address = addr_match.group(0).strip()
                    break
        if address:
            break
    
    # If we have name from first line, use it; otherwise try LLM
    if first_name and last_name:
        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "address": address
        }
    
    # Fallback to LLM for more complex cases
    sys_prompt = (
        "You extract personal contact information from résumés. "
        "Return ONLY JSON. Use null for missing fields. Do not invent information. "
        "The name is typically the first line or at the very top of the resume."
    )
    
    user_prompt = f"""
Resume Text (verbatim):
---
{resume_text}
---

IMPORTANT INSTRUCTIONS:
1. The person's FULL NAME is almost always at the very TOP of the resume, typically the first line.
2. Look for a line that contains typically 2-3 words (first name and last name) at the beginning.
3. Split the full name into first_name and last_name correctly.

Task:
Extract the following personal information if present:
- first_name: First name of the person (MUST extract from the top of the resume)
- last_name: Last name of the person (MUST extract from the top of the resume)
- email: Email address (usually contains @ symbol)
- phone: Phone number
- address: Full home address if present

Output JSON format:
{{
  "first_name": "John" or null,
  "last_name": "Doe" or null,
  "email": "john.doe@example.com" or null,
  "phone": "+1 (555) 123-4567" or null,
  "address": "123 Main St, City, State 12345" or null
}}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-5.1",
            temperature=0.1,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        llm_first_name = data.get("first_name")
        llm_last_name = data.get("last_name")
        
        # Use LLM results if we didn't get name from first line, or merge if LLM found better info
        if not first_name:
            first_name = llm_first_name
        if not last_name:
            last_name = llm_last_name
        
        # Use LLM email/phone if we didn't find them via regex
        if not email:
            email = data.get("email")
        if not phone:
            phone = data.get("phone")
        if not address:
            address = data.get("address")
        
        # Final fallback: extract from first line if still no name
        if not first_name and not last_name and lines:
            first_line = lines[0]
            if first_line and len(first_line.split()) >= 2:
                name_parts = first_line.split()
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
        
        # Ensure we strip whitespace and handle None values
        first_name = first_name.strip() if first_name else None
        last_name = last_name.strip() if last_name else None
        
        # If we have a name but it's not split correctly, try to split it
        # Sometimes the LLM might return the full name in first_name or last_name
        if first_name and not last_name:
            # Check if first_name contains multiple words (full name)
            if len(first_name.split()) > 1:
                name_parts = first_name.split()
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
        elif last_name and not first_name:
            # Check if last_name contains multiple words (full name)
            if len(last_name.split()) > 1:
                name_parts = last_name.split()
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
        
        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "address": address
        }
    except Exception as e:
        print(f"Warning: Error in LLM extraction: {e}")
        # Return what we extracted from regex, with same name splitting logic
        first_name_clean = first_name.strip() if first_name else None
        last_name_clean = last_name.strip() if last_name else None
        
        # If we have a name but it's not split correctly, try to split it
        if first_name_clean and not last_name_clean:
            if len(first_name_clean.split()) > 1:
                name_parts = first_name_clean.split()
                first_name_clean = name_parts[0]
                last_name_clean = ' '.join(name_parts[1:])
        elif last_name_clean and not first_name_clean:
            if len(last_name_clean.split()) > 1:
                name_parts = last_name_clean.split()
                first_name_clean = name_parts[0]
                last_name_clean = ' '.join(name_parts[1:])
        
        return {
            "first_name": first_name_clean,
            "last_name": last_name_clean,
            "email": email,
            "phone": phone,
            "address": address
        }

# --- 4) Extract company information from job description ---
def extract_company_info_from_job(job_text: str) -> Dict[str, Optional[str]]:
    """
    Extract company information from job description text.
    Returns: {company_name, company_address}
    """
    sys_prompt = (
        "You extract company information from job descriptions. "
        "Return ONLY JSON. Use null for missing fields. Do not invent information."
    )
    user_prompt = f"""
Job Description Text (verbatim):
---
{job_text}
---

Task:
Extract the following company information if present:
- company_name: Name of the company/organization
- company_address: Full company address (street, city, state, zip) if mentioned

Output JSON format:
{{
  "company_name": "Acme Corporation" or null,
  "company_address": "456 Business St, City, State 67890" or null
}}

If the address is not explicitly mentioned, set company_address to null.
"""
    resp = client.chat.completions.create(
        model="gpt-5.1",
        temperature=0.1,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(resp.choices[0].message.content)
        return {
            "company_name": data.get("company_name"),
            "company_address": data.get("company_address")
        }
    except Exception:
        return {
            "company_name": None,
            "company_address": None
        }

# --- 5) Projects/experiences via LLM ---
def extract_projects_from_resume(resume_text: str) -> List[Dict[str, str]]:
    """
    Returns a list of up to 4 projects/experiences found in resume_text.
    Each item: {title, technologies, description, achievements}
    """
    sys_prompt = (
        "You extract projects and experiences from résumés. "
        "Return ONLY JSON. Do not invent facts."
    )
    user_prompt = f"""
Resume Text (verbatim):
---
{resume_text}
---

Task:
- Identify the 2–4 most relevant projects or experiences that would help a cover letter.
- Use ONLY info present in the resume.
- For each, fill fields:
  - title (string)
  - technologies (short comma-separated string; DO NOT add technologies not in the resume)
  - description (1 sentence)
  - achievements (1 bullet-like sentence; if metrics present, include them)

Output JSON format:
{{
  "projects": [
    {{"title": "...", "technologies": "...", "description": "...", "achievements": "..."}}
  ]
}}
"""
    resp = client.chat.completions.create(
        model="gpt-5.1",
        temperature=0.2,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(resp.choices[0].message.content)
        items = data.get("projects", [])
    except Exception:
        items = []
    # Normalize
    out = []
    for p in items:
        out.append({
            "title": str(p.get("title", "")).strip(),
            "technologies": str(p.get("technologies", "")).strip(),
            "description": str(p.get("description", "")).strip(),
            "achievements": str(p.get("achievements", "")).strip(),
        })
    # Deduplicate by title
    seen = set()
    uniq = []
    for p in out:
        t = p["title"].lower()
        if t in seen or not p["title"]:
            continue
        seen.add(t)
        uniq.append(p)
    return uniq[:4]

# --- 6) Replace template placeholders with extracted information ---
def fill_template_placeholders(
    template: str,
    personal_info: Dict[str, Optional[str]],
    company_info: Dict[str, Optional[str]],
    current_date: str
) -> str:
    """
    Replace placeholders in template with extracted information.
    For missing fields, uses placeholder text like "[replace with contact number - or remove it if not needed]".
    """
    lines = template.split('\n')
    result_lines = []
    i = 0
    
    # First pass: replace placeholders
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Replace name
        if line_stripped == "First Last Name":
            full_name = ""
            # Try to construct full name from first_name and last_name
            if personal_info.get("first_name") and personal_info.get("last_name"):
                full_name = f"{personal_info['first_name']} {personal_info['last_name']}"
            elif personal_info.get("first_name"):
                full_name = personal_info['first_name']
            elif personal_info.get("last_name"):
                full_name = personal_info['last_name']
            
            if full_name:
                result_lines.append(full_name.strip())
            else:
                result_lines.append("[replace with your name]")
            i += 1
        
        # Replace email
        elif line_stripped == "Email Address":
            email = personal_info.get("email")
            if email:
                result_lines.append(email)
            else:
                result_lines.append("[replace with email address]")
            i += 1
        
        # Replace phone
        elif line_stripped == "Contact Number":
            phone = personal_info.get("phone")
            if phone:
                result_lines.append(phone)
            else:
                result_lines.append("[replace with contact number - or remove it if not needed]")
            i += 1
        
        # Replace date
        elif line_stripped == "Date of application submission":
            # Before adding date, check if we need to insert address
            # Address should go after contact info, before date
            address = personal_info.get("address")
            if address and not any(address in line for line in result_lines):
                # Check if we just processed contact number
                if result_lines and (
                    "[replace with contact number" in result_lines[-1] or 
                    (personal_info.get("phone") and personal_info.get("phone") in result_lines[-1])
                ):
                    # Insert blank line and address before date
                    result_lines.append("")
                    result_lines.append(address)
            
            result_lines.append(current_date)
            i += 1
        
        # Keep blank lines
        elif line_stripped == "":
            result_lines.append(line)
            i += 1
        
        # Replace company name
        elif line_stripped == "Company Name":
            company_name = company_info.get("company_name")
            if company_name:
                result_lines.append(company_name)
            else:
                result_lines.append("[replace with company name]")
            i += 1
        
        # Replace company street
        elif line_stripped == "Company Street":
            company_address = company_info.get("company_address")
            if company_address:
                # Try to split address into street and city/state
                # Common patterns: "123 Street, City, State ZIP" or "123 Street, City, State"
                address_parts = company_address.split(", ")
                if len(address_parts) >= 2:
                    # First part is usually street
                    street = address_parts[0]
                    result_lines.append(street)
                    # Check if next line is "Company City, State"
                    if i + 1 < len(lines) and lines[i + 1].strip() == "Company City, State":
                        # City, State is the rest
                        city_state = ", ".join(address_parts[1:])
                        result_lines.append(city_state)
                        i += 2  # Skip both street and city/state lines
                        continue
                    else:
                        # No separate city/state line, put everything on street line
                        result_lines[-1] = company_address
                else:
                    # Can't split (only one part), put full address on street line
                    # Mark that we need a placeholder for city/state
                    result_lines.append(company_address)
                    # Check if next line is "Company City, State" - if so, we'll handle it
                    if i + 1 < len(lines) and lines[i + 1].strip() == "Company City, State":
                        # We'll add placeholder for city/state in the next iteration
                        pass
            else:
                result_lines.append("[replace with company street - or remove it if not needed]")
            i += 1
        
        # Replace company city/state
        elif line_stripped == "Company City, State":
            # Check if street was already processed
            if result_lines:
                last_line = result_lines[-1].strip()
                company_address = company_info.get("company_address")
                
                # Check if city/state was already added (when we processed street with multiple parts)
                # If the last line contains ", " and is part of the address, city/state was already added
                if company_address and ", " in company_address:
                    address_parts = company_address.split(", ")
                    if len(address_parts) >= 2:
                        city_state_part = ", ".join(address_parts[1:])
                        # If last line is the city/state part, it was already added
                        if last_line == city_state_part:
                            # City/state already added, skip this line
                            i += 1
                            continue
                        # If last line is the full address, we need to add city/state separately
                        elif last_line == company_address:
                            # Full address on street line, add city/state part
                            result_lines.append(city_state_part)
                            i += 1
                            continue
                
                # If we have an address but it was put on street line as a single part (no ", ")
                if company_address and company_address == last_line and ", " not in company_address:
                    # Address couldn't be split, so city/state needs placeholder
                    result_lines.append("[replace with company city, state - or remove it if not needed]")
                elif "[replace with company street" in last_line or not company_address:
                    # Street wasn't processed or address not found, add placeholder
                    result_lines.append("[replace with company city, state - or remove it if not needed]")
                # Otherwise, city/state was already handled above, so skip
            else:
                result_lines.append("[replace with company city, state - or remove it if not needed]")
            i += 1
        
        # Keep all other lines as-is
        else:
            result_lines.append(line)
            i += 1
    
    # Join lines and clean up extra blank lines (more than 2 consecutive)
    result = '\n'.join(result_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Post-processing: If we still have "First Last Name" placeholders but we have a name in the signature,
    # extract it and replace the placeholder
    if "[replace with your name]" in result or "First Last Name" in result:
        # Look for the name in the signature area (after "Sincerely,")
        signature_match = re.search(r'Sincerely,.*?\n+([A-Za-z]+(?:\s+[A-Za-z-]+)+)', result, re.IGNORECASE | re.DOTALL)
        if signature_match:
            extracted_name = signature_match.group(1).strip()
            # Replace any remaining placeholders with the extracted name
            result = result.replace("[replace with your name]", extracted_name)
            result = result.replace("First Last Name", extracted_name)
        # Also try to construct from personal_info one more time
        elif personal_info.get("first_name") or personal_info.get("last_name"):
            full_name = ""
            if personal_info.get("first_name") and personal_info.get("last_name"):
                full_name = f"{personal_info['first_name']} {personal_info['last_name']}"
            elif personal_info.get("first_name"):
                full_name = personal_info['first_name']
            elif personal_info.get("last_name"):
                full_name = personal_info['last_name']
            if full_name:
                result = result.replace("[replace with your name]", full_name.strip())
                result = result.replace("First Last Name", full_name.strip())
    
    return result

# --- 7) Draft the body with LLM (constrained to resume-only info) ---
def draft_body(resume_text: str,
               job_text: str,
               skills: Dict[str, List[str]],
               projects: List[Dict[str, str]],
               style_example: Optional[str] = None,
               style_paragraphs: Optional[List[str]] = None) -> Tuple[str, Dict[str, List[str]]]:
    """
    Draft the cover letter body using LLM, constrained to resume-only info.
    
    Args:
        resume_text: Raw resume text content
        job_text: Job description text
        skills: Extracted skills from resume
        projects: Extracted projects/experiences from resume
        style_example: Optional example cover letter to mimic writing style.
                      If provided, the LLM will match tone and formality but
                      will NOT copy sentences, phrases, dates, or company names.
        style_paragraphs: Optional list of paragraphs from style_example.
                          Used to match paragraph count, narrative flow, and structure.
    
    Returns:
        Tuple of (body_text, meta) where meta contains 'skills_used' and 'projects_referenced'.
    """
    # Flatten skills for readability
    flat_skills = _safe_unique(
        skills.get("ProgrammingLanguages", [])
        + skills.get("FrameworksLibraries", [])
        + skills.get("ToolsPlatforms", []),
        limit=18
    )
    projects_compact = [
        f"- {p['title']} ({p['technologies']}) — {p['achievements'] or p['description']}"
        for p in projects
    ][:3]

    sys_prompt = (
        "You write concise, professional cover-letter paragraphs that ONLY use information "
        "provided in the resume: skills and projects. Do not invent employers, dates, or technologies. "
        "Keep it ~150–220 words, 2–3 paragraphs, direct and impact-focused."
    )

    # Build paragraph structure block if provided
    paragraph_style_block = ""
    if style_paragraphs:
        n_paragraphs = len(style_paragraphs)
        summarized = [
            f"- Paragraph {i+1}: {p[:220]}..." for i, p in enumerate(style_paragraphs)
        ]
        paragraph_style_block = f"""

Paragraph structure of my previous cover letter:

{chr(10).join(summarized)}



You MUST produce **exactly {n_paragraphs} paragraphs** in the new body.

Each paragraph should serve a similar narrative purpose and order

(e.g., introduction, past experience, current project, technical skills, motivation/fit, closing),

but all wording must be new and all content must come only from my resume and the job description.

Separate paragraphs using a single blank line.

"""

    # Build style example block if provided
    style_block = ""
    if style_example:
        style_block = f"""

Here is an example of my previous cover letter.

Mimic its tone, level of formality, and general sentence rhythm,

but DO NOT copy any sentences, phrases, company names, or dates.

Treat it ONLY as a style reference:



---

{style_example}

---

"""

    # Build the user prompt with all components
    user_prompt = f"""
Resume skills (canonicalized, resume-only):

---

{json.dumps(flat_skills, ensure_ascii=False)}

---



Projects / experiences from the resume:

---

{chr(10).join(projects_compact) if projects_compact else "None"}

---



Job description (verbatim, may be long):

---

{job_text}

---



{style_block}{paragraph_style_block}
Write ONLY the BODY of the cover letter (no greeting/salutation and no closing/sign-off).



Requirements:

- Use only information from my resume and the job description.

- Mention 5–8 of the above skills naturally and credibly.

- Reference 1–2 of the listed projects with specific contributions or outcomes.

- Follow the paragraph structure described above and output **exactly** that many paragraphs.

- Separate paragraphs with a single blank line.

- Do not include headers, contact details, dates, or signatures.

"""

    resp = client.chat.completions.create(
        model="gpt-5.1",
        temperature=0.4,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    body = resp.choices[0].message.content.strip()

    # Heuristically record which items were used
    used_sk = [s for s in flat_skills if re.search(rf"\b{re.escape(s)}\b", body, re.IGNORECASE)]
    used_proj = []
    for p in projects:
        if p["title"] and re.search(rf"\b{re.escape(p['title'])}\b", body, re.IGNORECASE):
            used_proj.append(p["title"])

    meta = {
        "skills_used": used_sk[:10],
        "projects_referenced": used_proj[:2],
    }
    return body, meta

# --- 8) API-friendly function ---
def generate_cover_letter_from_text(
    resume_text: str,
    job_text: str,
    template_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate cover letter from resume text, job text, and optional template text.
    
    Args:
        resume_text: Raw resume text content
        job_text: Job description text
        template_text: Optional template text. If provided:
            - If it contains BODY markers (<<BODY>>, {{BODY}}, etc.), treats it as a real template
            - If it does NOT contain BODY markers, treats it as a style example (old cover letter)
            - If None, uses default CTP template
    
    Returns:
        Dictionary with:
        - cover_letter: The final cover letter text
        - skills_used: List of skills mentioned in the letter
        - projects_referenced: List of projects mentioned in the letter
        - skills_all: All skills extracted from resume
        - projects_all: All projects extracted from resume
    """
    # 1) Distinguish between real template and style example
    body_markers = ("<<BODY>>", "{{BODY}}", "[[BODY]]", "[BODY]")
    style_example = None
    style_paragraphs = None
    
    if template_text:
        has_body_marker = any(marker in template_text for marker in body_markers)
        
        if has_body_marker:
            # Case 1: user provided a real template with a BODY marker
            # → use it directly as the layout template
            template = template_text
        else:
            # Case 2: user uploaded an old finished cover letter
            # → use it only for style + paragraph structure
            template = _load_template(None)  # keep using the existing CTP template
            style_example = template_text
            
            # derive paragraph structure - handle both line breaks and period separators
            style_paragraphs = _extract_paragraphs(template_text)
    else:
        # No optional file → behave as today
        template = _load_template(None)
    
    # 2) Extract personal information from resume
    personal_info = extract_personal_info_from_resume(resume_text)
    
    # 3) Extract company information from job description
    company_info = extract_company_info_from_job(job_text)
    
    # 4) Get current date
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # 5) Fill template placeholders with extracted information
    template = fill_template_placeholders(template, personal_info, company_info, current_date)
    
    # 6) Extract skills via extract_skills.py script
    skills = extract_skills_with_script(resume_text)
    
    # 7) Extract projects from resume
    projects = extract_projects_from_resume(resume_text)
    
    # 8) Draft body + inject into template
    # Pass style_example and style_paragraphs to draft_body so it can mimic writing style and structure
    body, meta = draft_body(
        resume_text, 
        job_text, 
        skills, 
        projects, 
        style_example=style_example,
        style_paragraphs=style_paragraphs
    )
    letter = _inject_body_into_template(template, body)
    
    # 9) Return result dictionary
    return {
        "cover_letter": letter,
        "skills_used": meta["skills_used"],
        "projects_referenced": meta["projects_referenced"],
        "skills_all": skills,
        "projects_all": projects
    }

# --- 6) Main entry ---
def main():
    parser = argparse.ArgumentParser(description="Generate a tailored cover letter (Phase 2).")
    parser.add_argument("--resume", required=True, help="Path to resume (PDF or TXT).")
    parser.add_argument("--job", required=True, help="Path to job description .txt.")
    parser.add_argument("--template", required=False, help="Path to cover-letter template (.txt, .pdf, or .docx).")
    parser.add_argument("--out", required=False, default="cover_letter.txt", help="Output cover letter .txt path.")
    parser.add_argument("--meta", required=False, default="cover_letter_meta.json", help="Output meta JSON path.")
    args = parser.parse_args()

    resume_path = Path(args.resume)
    job_path = Path(args.job)
    template_path = Path(args.template) if args.template else None
    out_txt = Path(args.out)
    out_meta = Path(args.meta)

    if not resume_path.exists():
        print(f"❌ Resume file not found: {resume_path}")
        sys.exit(1)
    if not job_path.exists():
        print(f"❌ Job file not found: {job_path}")
        sys.exit(1)

    # Load texts
    resume_text = load_resume_text(resume_path)
    job_text = _read_text_file(job_path)
    template_text = load_template_file(template_path) if template_path else None

    # Use the API-friendly function which handles all extraction and template filling
    result = generate_cover_letter_from_text(resume_text, job_text, template_text)

    # Persist
    out_txt.write_text(result["cover_letter"], encoding="utf-8")
    payload = {
        "skills_used": result["skills_used"],
        "projects_referenced": result["projects_referenced"],
        "skills_all": result["skills_all"],
        "projects_all": result["projects_all"],
        "resume_chars": len(resume_text),
        "job_chars": len(job_text),
        "template_path": str(template_path) if template_path else None,
        "output_txt": str(out_txt),
    }
    out_meta.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print a short JSON to stdout (useful for a web route)
    print(json.dumps({
        "ok": True,
        "output_txt": str(out_txt),
        "skills_used": result["skills_used"],
        "projects_referenced": result["projects_referenced"]
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
