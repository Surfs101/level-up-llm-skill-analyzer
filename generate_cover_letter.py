"""
generate_cover_letter.py
Cover Letter Generator - Single LLM Call Approach

What it does
------------
Generates a complete, tailored cover letter from resume and job description using a single
optimized LLM call. The LLM analyzes the resume and job description, then generates a cover
letter following the template's exact style, narrative structure, and formatting.

Usage
-----
CLI:
  python generate_cover_letter.py --resume resume.pdf --job job.txt --template template.txt

API:
  from generate_cover_letter import generate_cover_letter_from_text
  result = generate_cover_letter_from_text(resume_text, job_text, template_text=None)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from dotenv import load_dotenv
from openai import OpenAI

# --- ENV / CLIENT ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY missing in environment.")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)


def _read_text_file(path: Path) -> str:
    """Read text file with UTF-8 encoding."""
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_default_template() -> str:
    """Load the default CTP_template.txt from the same directory as this script."""
    default_template_path = Path(__file__).parent / "CTP_template.txt"
    if default_template_path.exists():
        return _read_text_file(default_template_path)
    # Fallback to minimal template if CTP_template.txt doesn't exist
    return (
        "First Last Name\n"
        "Email Address\n"
        "Contact Number\n\n"
        "Date of application submission\n\n"
        "Company Name\n"
        "Company Street\n"
        "Company City, State\n\n"
        "Dear Hiring Manager:\n\n"
        "<<BODY>>\n\n"
        "Thank you for your time and consideration.\n\n"
        "Sincerely,\n"
        "First Last Name"
    )


def load_template_file(template_path: Path) -> str:
    """
    Load a template file and convert it to plain text.
    Supports .txt, .pdf, and .docx formats.
    
    Args:
        template_path: Path to the template file
        
    Returns:
        Template text content as string
        
    Raises:
        RuntimeError: If file cannot be read or converted
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    ext = template_path.suffix.lower()
    
    # Plain text files
    if ext in {".txt", ".text", ".md"}:
        return _read_text_file(template_path)
    
    # PDF files
    if ext == ".pdf":
        try:
            from pdf_resume_parser import PDFToTextConverter
        except ImportError as e:
            raise RuntimeError(
                "pdf_resume_parser.PDFToTextConverter is required to use PDF templates. "
                "Install it or use a .txt template instead."
            ) from e
        
        converter = PDFToTextConverter(str(template_path))
        if not converter.convert():
            raise RuntimeError(f"Failed to convert PDF template to text: {template_path}")
        return converter.cleaned_text
    
    # Word documents (.doc, .docx)
    if ext in {".doc", ".docx"}:
        try:
            from docx import Document
        except ImportError as e:
            raise RuntimeError(
                "python-docx is required to use .doc/.docx templates. "
                "Install with: pip install python-docx"
            ) from e
        
        doc = Document(str(template_path))
        # Join paragraphs with blank lines to preserve structure
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    
    # Fallback: try to read as text anyway
    return _read_text_file(template_path)


def _generate_cover_letter_with_default_template(
    resume_text: str,
    job_text: str
) -> Dict[str, Any]:
    """
    Generate a complete cover letter using the default CTP template.
    
    Uses a single LLM call to analyze the resume and job description, then generate a complete
    cover letter following the default template's style, narrative structure, and formatting.

    Args:
        resume_text: Raw resume text content (required)
        job_text: Job description text (required)
    
    Returns:
        Dictionary with:
        - cover_letter: Complete cover letter text with all placeholders filled
        - metadata: Optional metadata (can be extended in future)
    """
    # Load default template
    template = _load_default_template()
    
    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")

    # Build comprehensive prompt for single LLM call
    system_prompt = """You are an expert cover letter writer. Your task is to analyze a resume and job description, 
then generate a complete, professional cover letter that follows the provided template's EXACT style, 
narrative structure, formatting, and structural blueprint.

CRITICAL REQUIREMENTS - THE TEMPLATE IS A STRICT BLUEPRINT:
1. **TEMPLATE CONTENT IS EXAMPLE/PLACEHOLDER DATA**: The template may contain actual names, companies, dates, experiences, or other specific information. These are PLACEHOLDERS showing the structure - you MUST REPLACE them ALL with information from the resume and job description. NEVER use information from the template content itself.

2. Use ONLY information from the resume and job description - do not invent skills, experiences, or qualifications, and NEVER copy information from the template content

3. COUNT the body paragraphs in the template and produce EXACTLY the same number

4. Match the template's narrative flow - if template starts with "I heard about...", your output should start similarly

5. Match the template's language style exactly - if template uses "I am" vs "I'm", follow that pattern

6. Match sentence structure and length patterns from the template

7. Each output paragraph should mirror the corresponding template paragraph:
   - Same narrative purpose (introduction, experience description, closing)
   - Same general structure and flow
   - Same level of detail and approximate length

8. Replace ALL specific information in the template (names, emails, phones, addresses, company names, dates, job titles, specific projects/courses) with actual data from resume and job description

9. AVOID DUPLICATION: If information appears in multiple template locations, use it only ONCE

10. For missing information, use placeholder format: "[provide {field} - remove it if not needed]"

11. Preserve ALL formatting: line breaks, spacing, paragraph breaks exactly as in template

12. Write in a natural, authentic, human style - avoid robotic or overly formal AI-generated tone

13. The template body paragraphs are a STRUCTURAL BLUEPRINT - extract only the structure, style, and narrative patterns, NOT the actual content"""

    user_prompt = f"""Analyze the resume and job description, then generate a complete cover letter following the template.

RESUME TEXT:
---
{resume_text}
---

JOB DESCRIPTION:
---
{job_text}
---

TEMPLATE TO FOLLOW:
---
{template}
---

CURRENT DATE: {current_date}

TASK:
1. FIRST: Analyze the template to identify STRUCTURAL elements vs. REPLACEABLE content:
   - **STRUCTURAL ELEMENTS (KEEP THESE PATTERNS):**
     * Count the EXACT number of body paragraphs in the template (between greeting and closing)
     * Identify the narrative flow: how does each paragraph start? What is its purpose?
     * Note the language style: formal vs casual, sentence length, structure patterns
     * Study the opening sentence of each paragraph - what pattern does it follow?
     * Paragraph organization and structure
     * Formatting (line breaks, spacing, paragraph breaks)
   
   - **REPLACEABLE ELEMENTS (REPLACE WITH ACTUAL DATA):**
     * Personal information: names, emails, phone numbers, addresses
     * Company information: company names, company addresses
     * Dates: application dates, graduation dates, etc.
     * Job titles, role names, position titles
     * Specific projects, courses, programs, institutions mentioned
     * Specific skills, technologies, or experiences mentioned
     * Any other specific information that appears to be example/placeholder data
   
   - **CRITICAL**: The template contains EXAMPLE/PLACEHOLDER content. Extract ONLY the structural blueprint (paragraph organization, narrative flow, language style, formatting). You must REPLACE ALL specific information with actual data from the resume and job description. Do NOT copy any information from the template content itself.

2. Extract personal information from the resume:
   - Full name (first and last name from the top of the resume)
   - Email address
   - Phone number (if available)
   - Address (if available)

3. Extract company information from the job description:
   - Company name
   - Company address (if available)

4. Analyze the candidate's qualifications:
   - Key skills and technologies mentioned in the resume
   - Relevant projects and experiences
   - How these match the job requirements

5. Generate the complete cover letter following the template STRUCTURE EXACTLY:
   - **REPLACE ALL SPECIFIC INFORMATION IN THE TEMPLATE** (whether obvious placeholders or actual example data):
     * Personal information: Replace ALL names, emails, phone numbers, addresses with data from resume
       - "First Last Name" or any actual name (e.g., "John Doe") → candidate's full name from resume (appears in header and signature - use same name both times)
       - "Email Address" or any actual email → candidate's email from resume OR "[provide email - remove it if not needed]" if not found
       - "Contact Number" or any actual phone → candidate's phone number from resume OR "[provide contact number - remove it if not needed]" if not found
     
     * Company information: Replace ALL company names and addresses with data from job description
       - "Company Name" or any actual company name (e.g., "Kinship", "Acme Corp") → company name from job description OR "[provide company name - remove it if not needed]" if not found
       - "Company Street" or any actual address → company street address from job description (if available) OR "[provide company street - remove it if not needed]" if not found
       - "Company City, State" or any actual city/state → company city and state from job description (if available) OR "[provide company city, state - remove it if not needed]" if not found
     
     * Dates: Replace ALL dates with current date or appropriate dates from resume
       - "Date of application submission" or any actual date → current date ({current_date})
       - Any graduation dates, course dates, etc. → use dates from resume if available
     
     * Job titles, roles, positions: Replace with job title from job description
     
     * Specific experiences, projects, courses, programs: Replace with candidate's actual experiences from resume
       - If template mentions "I have had experience building mobile applications in Android" → replace with candidate's actual relevant experience from resume
       - If template mentions specific courses/programs (e.g., "CodePath Android Development course") → use as structure reference only, write new content based on candidate's actual courses/programs from resume
       - If template mentions specific projects → replace with candidate's actual projects from resume
     
     * Specific skills, technologies: Replace with candidate's actual skills from resume
   
   - CRITICAL: AVOID DUPLICATION
     * If company address appears in both "Company Street" and "Company City, State" lines, split it appropriately (street on one line, city/state on the other)
     * If you cannot split the address, put it on "Company Street" line and use "[provide company city, state - remove it if not needed]" for the city/state line
     * Do NOT repeat the same information in multiple places
   
   - Write body paragraphs that STRICTLY FOLLOW THE TEMPLATE STRUCTURE:
     * **CRITICAL WARNING**: NEVER use information from the template content itself. The template's body paragraphs contain EXAMPLE content showing the structure and style. Extract ONLY the structural patterns (paragraph organization, narrative flow, language style, sentence patterns) and write COMPLETELY NEW content based on the resume and job description.
     
     * Produce EXACTLY the same number of paragraphs as the template has
     * Each paragraph must mirror its corresponding template paragraph:
       - Same narrative purpose (e.g., first paragraph introduces, second describes experience, third closes)
       - Same opening style/pattern (if template starts with "I heard about...", start similarly)
       - Same general structure and flow
       - Same approximate length and level of detail
     * Match the template's language style exactly:
       - If template uses "I am" (not "I'm"), use "I am"
       - If template uses contractions, use contractions
       - Match the formality level exactly
     * Match sentence structure patterns from template:
       - Similar sentence length
       - Similar sentence complexity
       - Similar use of transitions and connectors
     * Write in a natural, authentic, human voice - avoid robotic or overly formal language
     * Use ONLY information from the resume and job description (no hallucination, and NEVER copy from template content)
     * Connect candidate's skills/experiences to job requirements naturally
     * Maintain professional, confident tone while sounding genuine and human
     * The narrative flow must match the template - if template tells a story in a certain order, follow that order

6. Output the COMPLETE cover letter with:
   - EXACT same number of body paragraphs as the template
   - Each paragraph mirroring its corresponding template paragraph's structure and purpose
   - All placeholders replaced with actual information OR placeholder format for missing info
   - NO DUPLICATION of information
   - ALL formatting preserved exactly (line breaks, spacing, paragraph breaks)
   - Body paragraphs written in natural, human style matching the template's tone
   - Narrative flow matching the template exactly
   - Language style matching the template exactly (formality, contractions, sentence patterns)
   - Ready to use as-is

OUTPUT:
Return ONLY the complete cover letter text. Do not include any explanations, metadata, or JSON formatting.
The output must be structurally identical to the template - same paragraph count, same narrative flow, same language style.
**FINAL CHECK**: Ensure you have replaced ALL specific information from the template (names, companies, dates, experiences, projects, skills) with actual information from the resume and job description. The output should contain NO information copied from the template content - only the structural patterns, style, and formatting.
The output should be ready to use as-is, with all placeholders filled and all content following the template's EXACT structure and style."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        cover_letter = response.choices[0].message.content.strip()
        
        if not cover_letter:
            raise ValueError("LLM did not generate cover letter content")

        return {
            "cover_letter": cover_letter,
            "metadata": {
                "resume_length": len(resume_text),
                "job_length": len(job_text),
                "template_used": "default",
                "generated_date": current_date,
            },
        }

    except Exception as e:
        raise RuntimeError(f"Failed to generate cover letter: {str(e)}") from e


def _generate_cover_letter_with_custom_template(
    resume_text: str,
    job_text: str,
    template_text: str
) -> Dict[str, Any]:
    """
    Generate a complete cover letter using a user-provided custom template.
    
    Uses a single LLM call to analyze the resume and job description, then generate a complete
    cover letter following the user-provided template's style, narrative structure, and formatting.

    Args:
        resume_text: Raw resume text content (required)
        job_text: Job description text (required)
        template_text: User-provided template text (should be plain text, already converted from .pdf/.docx if needed).
    
    Returns:
        Dictionary with:
        - cover_letter: Complete cover letter text with all placeholders filled
        - metadata: Optional metadata (can be extended in future)
    """
    template = template_text
    
    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")

    # Build comprehensive prompt for single LLM call
    system_prompt = """You are an expert cover letter writer. Your task is to analyze a resume and job description, 
then generate a complete, professional cover letter that follows the provided template's EXACT style, 
narrative structure, formatting, and structural blueprint.

CRITICAL REQUIREMENTS - TWO-PART APPROACH:
1. **HEADER/INFO SECTION (Before Body)**: Identify where the body starts (typically at "Dear Hiring Manager:" or similar greeting). 
   Everything BEFORE the body is the header/info section. You MUST replace ALL lines in this section with actual information 
   from the resume and job description. Replace names, emails, phones, addresses, dates, company names, company addresses 
   with actual data. Preserve the exact line structure and formatting, but replace the content.

2. **BODY SECTION (After Greeting)**: The body paragraphs contain EXAMPLE content showing structure and style. 
   Extract ONLY the structural patterns (paragraph organization, narrative flow, language style, sentence patterns) 
   and write COMPLETELY NEW content based on the resume and job description. NEVER use information from the template body content.

3. COUNT the body paragraphs in the template and produce EXACTLY the same number

4. Match the template's narrative flow - if template starts with "I heard about...", your output should start similarly

5. Match the template's language style exactly - if template uses "I am" vs "I'm", follow that pattern

6. Match sentence structure and length patterns from the template

7. Each output paragraph should mirror the corresponding template paragraph:
   - Same narrative purpose (introduction, experience description, closing)
   - Same general structure and flow
   - Same level of detail and approximate length

8. AVOID DUPLICATION: If information appears in multiple template locations, use it only ONCE

9. For missing information, use placeholder format: "[provide {field} - remove it if not needed]"

10. Preserve ALL formatting: line breaks, spacing, paragraph breaks exactly as in template

11. Write in a natural, authentic, human style - avoid robotic or overly formal AI-generated tone

12. Use ONLY information from the resume and job description - do not invent skills, experiences, or qualifications"""

    user_prompt = f"""Analyze the resume and job description, then generate a complete cover letter following the template.

RESUME TEXT:
---
{resume_text}
---

JOB DESCRIPTION:
---
{job_text}
---

TEMPLATE TO FOLLOW:
---
{template}
---

CURRENT DATE: {current_date}

TASK:
1. FIRST: Identify the HEADER/INFO SECTION and BODY SECTION:
   - Find where the body starts (look for "Dear Hiring Manager:" or similar greeting line like "Dear", "Hello", "To Whom It May Concern", etc.)
   - Everything BEFORE the greeting line is the HEADER/INFO SECTION
   - Everything AFTER the greeting line (including greeting) is the BODY SECTION
   - Count the EXACT number of body paragraphs in the template (between greeting and closing)

2. Extract personal information from the resume:
   - Full name (first and last name from the top of the resume)
   - Email address
   - Phone number (if available)
   - Address (if available)

3. Extract company information from the job description:
   - Company name
   - Company address (if available)

4. Analyze the candidate's qualifications:
   - Key skills and technologies mentioned in the resume
   - Relevant projects and experiences
   - How these match the job requirements

5. Generate the complete cover letter following the template STRUCTURE EXACTLY:
   
   **STEP A: REPLACE THE HEADER/INFO SECTION (Everything before the greeting):**
   - Go through each line in the header section BEFORE the greeting
   - Replace each line with actual information from resume and job description:
     * If line contains a name (e.g., "First Last Name", "John Doe") → replace with candidate's full name from resume
     * If line contains an email (e.g., "Email Address", "john@example.com") → replace with candidate's email from resume OR "[provide email - remove it if not needed]"
     * If line contains a phone (e.g., "Contact Number", "555-1234") → replace with candidate's phone from resume OR "[provide contact number - remove it if not needed]"
     * If line contains an address (candidate's address) → replace with candidate's address from resume OR "[provide address - remove it if not needed]"
     * If line contains a date (e.g., "Date of application submission", "January 1, 2024") → replace with current date ({current_date})
     * If line contains company name (e.g., "Company Name", "Kinship") → replace with company name from job description OR "[provide company name - remove it if not needed]"
     * If line contains company address/street → replace with company street address from job description OR "[provide company street - remove it if not needed]"
     * If line contains company city/state → replace with company city/state from job description OR "[provide company city, state - remove it if not needed]"
     * If line is blank → keep it as blank (preserve formatting)
   - **CRITICAL**: Preserve the exact line structure, spacing, and formatting of the header section. Only replace the content, not the structure.
   - **CRITICAL**: AVOID DUPLICATION - if company address appears in multiple lines, split it appropriately (street on one line, city/state on another) or use placeholders to avoid repetition
   
   **STEP B: REPLACE THE BODY SECTION (Everything after the greeting):**
   - Keep the greeting line exactly as it appears in the template (e.g., "Dear Hiring Manager:")
   - For body paragraphs, STRICTLY FOLLOW THE TEMPLATE STRUCTURE:
     * **CRITICAL WARNING**: NEVER use information from the template body content itself. The template's body paragraphs contain EXAMPLE content showing the structure and style. Extract ONLY the structural patterns (paragraph organization, narrative flow, language style, sentence patterns) and write COMPLETELY NEW content based on the resume and job description.
     
     * Produce EXACTLY the same number of paragraphs as the template has
     * Each paragraph must mirror its corresponding template paragraph:
       - Same narrative purpose (e.g., first paragraph introduces, second describes experience, third closes)
       - Same opening style/pattern (if template starts with "I heard about...", start similarly)
       - Same general structure and flow
       - Same approximate length and level of detail
     * Match the template's language style exactly:
       - If template uses "I am" (not "I'm"), use "I am"
       - If template uses contractions, use contractions
       - Match the formality level exactly
     * Match sentence structure patterns from template:
       - Similar sentence length
       - Similar sentence complexity
       - Similar use of transitions and connectors
     * Write in a natural, authentic, human voice - avoid robotic or overly formal language
     * Use ONLY information from the resume and job description (no hallucination, and NEVER copy from template content)
     * Connect candidate's skills/experiences to job requirements naturally
     * Maintain professional, confident tone while sounding genuine and human
     * The narrative flow must match the template - if template tells a story in a certain order, follow that order
   
   **STEP C: REPLACE THE SIGNATURE LINE:**
   - The LAST LINE of the template (signature line) must be replaced with the candidate's full name from resume
   - If the template ends with "First Last Name" or any name, replace it with the candidate's actual full name
   - Keep any closing phrases before the signature (e.g., "Sincerely,", "Best regards,") exactly as they appear in the template

6. Output the COMPLETE cover letter with:
   - Header section: All lines replaced with actual information from resume and job description, preserving exact structure and formatting
   - EXACT same number of body paragraphs as the template
   - Each paragraph mirroring its corresponding template paragraph's structure and purpose
   - All placeholders replaced with actual information OR placeholder format for missing info
   - NO DUPLICATION of information
   - ALL formatting preserved exactly (line breaks, spacing, paragraph breaks)
   - Body paragraphs written in natural, human style matching the template's tone
   - Narrative flow matching the template exactly
   - Language style matching the template exactly (formality, contractions, sentence patterns)
   - Signature line replaced with candidate's full name
   - Ready to use as-is

OUTPUT:
Return ONLY the complete cover letter text. Do not include any explanations, metadata, or JSON formatting.
The output must be structurally identical to the template - header section with replaced info, same paragraph count, same narrative flow, same language style.
**FINAL CHECK**: 
- Header section: Ensure ALL lines before the greeting have been replaced with actual information from resume and job description
- Body section: Ensure you have written COMPLETELY NEW content based on resume and job description, following only the structural patterns from the template
- Signature: Ensure the last line is the candidate's full name from the resume
The output should be ready to use as-is, with all placeholders filled and all content following the template's EXACT structure and style."""

    try:
        response = client.chat.completions.create(
        model="gpt-5.1",
            temperature=0.35,  # Higher temperature for more natural, human-sounding writing
        messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        cover_letter = response.choices[0].message.content.strip()
        
        if not cover_letter:
            raise ValueError("LLM did not generate cover letter content")
        
        return {
            "cover_letter": cover_letter,
            "metadata": {
                "resume_length": len(resume_text),
                "job_length": len(job_text),
                "template_used": "user_provided",
                "generated_date": current_date
            }
        }
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate cover letter: {str(e)}") from e


def generate_cover_letter_from_text(
    resume_text: str,
    job_text: str,
    template_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete cover letter from resume text, job description, and optional template.
    
    This function automatically selects the appropriate generation method:
    - If template_text is None: Uses default CTP_template.txt
    - If template_text is provided: Uses custom template with structural analysis

    Args:
        resume_text: Raw resume text content (required)
        job_text: Job description text (required)
        template_text: Optional template text. If None, uses default CTP_template.txt.
                      If provided, should be plain text (already converted from .pdf/.docx if needed).
    
    Returns:
        Dictionary with:
        - cover_letter: Complete cover letter text with all placeholders filled
        - metadata: Optional metadata (can be extended in future)
    """
    if template_text:
        # User provided a custom template
        return _generate_cover_letter_with_custom_template(
            resume_text=resume_text,
            job_text=job_text,
            template_text=template_text
        )
    else:
        # No template provided - use default template
        return _generate_cover_letter_with_default_template(
            resume_text=resume_text,
            job_text=job_text
        )


# --- CLI Entry Point ---
def main():
    """Command-line interface for cover letter generation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate a tailored cover letter from resume and job description."
    )
    parser.add_argument(
        "--resume",
        required=True,
        help="Path to resume file (PDF or TXT)"
    )
    parser.add_argument(
        "--job",
        required=True,
        help="Path to job description file (TXT)"
    )
    parser.add_argument(
        "--template",
        required=False,
        help="Path to cover letter template (.txt, .pdf, or .docx). If not provided, uses default CTP_template.txt"
    )
    parser.add_argument(
        "--out",
        required=False,
        default="cover_letter.txt",
        help="Output file path for the generated cover letter (default: cover_letter.txt)"
    )
    parser.add_argument(
        "--meta",
        required=False,
        default="cover_letter_meta.json",
        help="Output file path for metadata JSON (default: cover_letter_meta.json)"
    )

    args = parser.parse_args()
    
    # Validate input files
    resume_path = Path(args.resume)
    job_path = Path(args.job)
    template_path = Path(args.template) if args.template else None
    out_path = Path(args.out)
    meta_path = Path(args.meta)
    
    if not resume_path.exists():
        print(f"❌ Resume file not found: {resume_path}")
        sys.exit(1)
    
    if not job_path.exists():
        print(f"❌ Job description file not found: {job_path}")
        sys.exit(1)
    
    # Load resume text (handle PDF if needed)
    if resume_path.suffix.lower() == ".pdf":
        try:
            from pdf_resume_parser import PDFToTextConverter
        except ImportError:
            print("❌ pdf_resume_parser not available. Cannot process PDF resume.")
            sys.exit(1)
        
        converter = PDFToTextConverter(str(resume_path))
        if not converter.convert():
            print(f"❌ Failed to convert PDF resume: {resume_path}")
            sys.exit(1)
        resume_text = converter.cleaned_text
    else:
        resume_text = _read_text_file(resume_path)
    
    # Load job description
    job_text = _read_text_file(job_path)
    
    # Load template if provided
    template_text = None
    if template_path:
        try:
            template_text = load_template_file(template_path)
        except Exception as e:
            print(f"❌ Failed to load template: {e}")
            sys.exit(1)
    
    # Generate cover letter
    try:
        result = generate_cover_letter_from_text(
            resume_text=resume_text,
            job_text=job_text,
            template_text=template_text
        )
    except Exception as e:
        print(f"❌ Failed to generate cover letter: {e}")
        sys.exit(1)
    
    # Write output files
    out_path.write_text(result["cover_letter"], encoding="utf-8")
    meta_path.write_text(
        json.dumps(result["metadata"], indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"✅ Cover letter generated successfully!")
    print(f"   Output: {out_path}")
    print(f"   Metadata: {meta_path}")
    
    # Print summary to stdout
    print(json.dumps({
        "ok": True,
        "output_file": str(out_path),
        "metadata": result["metadata"]
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
