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
        stdout = proc.stdout.strip()
        # Try to locate the final JSON in stdout
        json_match = re.search(r"\{[\s\S]*\}$", stdout)
        if not json_match:
            # Sometimes the script prints logs; search for a JSON block
            raise RuntimeError(f"Could not parse skills JSON from extract_skills.py output:\n{stdout}\nSTDERR:\n{proc.stderr}")

        data = json.loads(json_match.group(0))
        skills = data.get("skills", {})
        # Ensure schema presence
        for k in ("ProgrammingLanguages", "FrameworksLibraries", "ToolsPlatforms"):
            skills.setdefault(k, [])
        return skills
    finally:
        try:
            os.remove(tmp_name)
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
            model="gpt-4o-mini",
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
        
        return {
            "first_name": first_name.strip() if first_name else None,
            "last_name": last_name.strip() if last_name else None,
            "email": email,
            "phone": phone,
            "address": address
        }
    except Exception as e:
        print(f"Warning: Error in LLM extraction: {e}")
        # Return what we extracted from regex
        return {
            "first_name": first_name.strip() if first_name else None,
            "last_name": last_name.strip() if last_name else None,
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
        model="gpt-4o-mini",
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
        model="gpt-4o-mini",
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
    Removes lines for missing optional fields (phone, address, company_address).
    """
    lines = template.split('\n')
    result_lines = []
    i = 0
    address_added = False
    last_contact_index = -1
    
    # First pass: replace placeholders and track contact info position
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Replace name
        if line_stripped == "First Last Name":
            full_name = ""
            if personal_info.get("first_name") and personal_info.get("last_name"):
                full_name = f"{personal_info['first_name']} {personal_info['last_name']}"
            elif personal_info.get("first_name"):
                full_name = personal_info['first_name']
            elif personal_info.get("last_name"):
                full_name = personal_info['last_name']
            if full_name:
                result_lines.append(full_name)
            else:
                result_lines.append(line)  # Keep placeholder if no name found
            i += 1
        
        # Replace email
        elif line_stripped == "Email Address":
            email = personal_info.get("email")
            if email:
                result_lines.append(email)
                last_contact_index = len(result_lines) - 1
            # Skip this line if email not found
            i += 1
        
        # Replace phone
        elif line_stripped == "Contact Number":
            phone = personal_info.get("phone")
            if phone:
                result_lines.append(phone)
                last_contact_index = len(result_lines) - 1
            # Skip this line if phone not found
            i += 1
        
        # Track when we're past contact section (before date)
        elif line_stripped == "Date of application submission":
            # Insert address before date if we have one and haven't added it
            address = personal_info.get("address")
            if address and not address_added and last_contact_index >= 0:
                # Find the right place to insert (after last contact, before date)
                # Add blank line and address before date
                result_lines.append("")  # Blank line
                result_lines.append(address)
                address_added = True
            
            result_lines.append(current_date)
            i += 1
        
        # Keep blank lines for now (will handle address insertion)
        elif line_stripped == "":
            # Only keep blank line if we're not about to insert address
            if not (address_added == False and personal_info.get("address") and last_contact_index >= 0):
                result_lines.append(line)
            i += 1
        
        # Replace company name
        elif line_stripped == "Company Name":
            company_name = company_info.get("company_name")
            if company_name:
                result_lines.append(company_name)
            # Skip this line if company name not found
            i += 1
        
        # Replace company street
        elif line_stripped == "Company Street":
            company_address = company_info.get("company_address")
            if company_address:
                # Split address into parts
                address_parts = company_address.split(", ")
                if len(address_parts) >= 2:
                    result_lines.append(address_parts[0])  # Street
                    # Check next line for city/state
                    if i + 1 < len(lines) and lines[i + 1].strip() == "Company City, State":
                        result_lines.append(", ".join(address_parts[1:]))  # City, State
                        i += 2  # Skip both street and city/state lines
                        continue
                    else:
                        result_lines.append(", ".join(address_parts[1:]))  # City, State on same line
                else:
                    result_lines.append(company_address)
            # Skip this line if address not found
            i += 1
        
        # Replace company city/state (should be handled above, but catch if needed)
        elif line_stripped == "Company City, State":
            # If we reach here, company street wasn't processed, so skip this line
            i += 1
        
        # Keep all other lines as-is
        else:
            result_lines.append(line)
            i += 1
    
    # If we still need to add address and haven't done so, add it after contact info
    if not address_added and personal_info.get("address") and last_contact_index >= 0:
        # Find insertion point: after last contact, before date
        date_idx = -1
        for idx, line in enumerate(result_lines):
            if "Date of application submission" in line or current_date in line:
                date_idx = idx
                break
        
        if date_idx > 0:
            # Insert address before date
            result_lines.insert(date_idx, "")
            result_lines.insert(date_idx + 1, personal_info.get("address"))
    
    # Join lines and clean up extra blank lines (more than 2 consecutive)
    result = '\n'.join(result_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result

# --- 7) Draft the body with LLM (constrained to resume-only info) ---
def draft_body(resume_text: str,
               job_text: str,
               skills: Dict[str, List[str]],
               projects: List[Dict[str, str]]) -> Tuple[str, Dict[str, List[str]]]:
    """
    Returns (body_text, meta) where meta contains 'skills_used' and 'projects_referenced'.
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

    user_prompt = f"""
Resume skills (canonicalized, resume-only):
{json.dumps(flat_skills, ensure_ascii=False)}

Projects/experiences (resume-only):
{json.dumps(projects, ensure_ascii=False)}

Job description (verbatim, may be long):
---
{job_text}
---

Write the BODY (no salutation, no sign-off) that:
- Aligns my resume skills/projects to the job’s needs.
- Mentions 5–8 of the above skills naturally.
- Cites 1–2 of the listed projects/experiences with a specific takeaway.
- Avoids any info not present in the resume.
- No headers, just prose paragraphs.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
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
        template_text: Optional template text (uses default if None)
    
    Returns:
        Dictionary with:
        - cover_letter: The final cover letter text
        - skills_used: List of skills mentioned in the letter
        - projects_referenced: List of projects mentioned in the letter
        - skills_all: All skills extracted from resume
        - projects_all: All projects extracted from resume
    """
    # 1) Load template (from text or use default)
    if template_text:
        template = template_text
    else:
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
    body, meta = draft_body(resume_text, job_text, skills, projects)
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
    parser.add_argument("--template", required=False, help="Path to cover-letter template .txt.")
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
    template_text = _read_text_file(template_path) if template_path else None

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
