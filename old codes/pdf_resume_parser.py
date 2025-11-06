import sys
import re
import os
from pathlib import Path
import argparse

try:
    import PyPDF2
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install PyPDF2 pytesseract pillow PyMuPDF")
    sys.exit(1)


class PDFToTextConverter:
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.raw_text = ""
        self.cleaned_text = ""
        self.metadata = {
            "pages_processed": 0,
            "used_ocr": False,
            "sections_detected": []
        }
    
    def extract_text(self):
        """Extract text from PDF, using OCR if needed."""
        try:
            # Try PyMuPDF first (faster)
            doc = fitz.open(self.pdf_path)
            text_content = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():
                    text_content.append(text)
                else:
                    # Use OCR for scanned pages
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    ocr_text = pytesseract.image_to_string(img)
                    text_content.append(ocr_text)
                    self.metadata["used_ocr"] = True
                
                self.metadata["pages_processed"] += 1
            
            self.raw_text = "\n".join(text_content)
            doc.close()
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return False
        
        return True
    
    def clean_text(self):
        """Clean and format the extracted text."""
        if not self.raw_text:
            return
        
        text = self.raw_text
        
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Fix hyphenated words split across lines
        text = re.sub(r'-\s*\n\s*', '', text)
        
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        
        # Clean up bullet points
        text = re.sub(r'^[\s•·▪▫‣⁃]\s*', '• ', text, flags=re.MULTILINE)
        
        # Detect and preserve section headers
        section_patterns = [
            r'^(EXPERIENCE|EDUCATION|SKILLS|PROJECTS|CERTIFICATIONS|AWARDS|SUMMARY|OBJECTIVE)',
            r'^(Work Experience|Professional Experience|Academic Background)',
            r'^(Technical Skills|Core Competencies|Languages)'
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            self.metadata["sections_detected"].extend(matches)
        
        # Final cleanup
        text = text.strip()
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 1:  # Skip single characters
                cleaned_lines.append(line)
        
        self.cleaned_text = '\n'.join(cleaned_lines)
    
    def save_output(self):
        """Save cleaned text to file."""
        base_name = self.pdf_path.stem
        cleaned_file = f"{base_name}_cleaned.txt"
        
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            f.write(self.cleaned_text)
        
        print(f"✓ Cleaned text saved to: {cleaned_file}")
    
    def convert(self):
        """Main conversion process."""
        if not self.pdf_path.exists():
            print(f"Error: PDF file '{self.pdf_path}' not found.")
            return False
        
        print(f"Processing: {self.pdf_path.name}")
        
        if not self.extract_text():
            return False
        
        self.clean_text()
        self.save_output()
        
        print(f"✓ Conversion complete! Processed {self.metadata['pages_processed']} pages.")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Convert PDF resume to clean text")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    
    args = parser.parse_args()
    
    converter = PDFToTextConverter(args.pdf_file)
    success = converter.convert()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    import io  # Import here to avoid issues if packages aren't installed
    main()
