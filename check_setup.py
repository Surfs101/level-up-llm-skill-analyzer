#!/usr/bin/env python3
"""
Setup verification script for AIJS-CTP-Capstone-Project
Checks if all required dependencies and environment variables are set up correctly.
"""

import sys
import os
from pathlib import Path

def check_env_file():
    """Check if .env file exists and contains OPENAI_API_KEY"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found in project root")
        print("   Please create a .env file with your OPENAI_API_KEY")
        return False
    
    # Load and check for API key
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        print("   Please add OPENAI_API_KEY=your_key_here to your .env file")
        return False
    
    if api_key.startswith("your_") or len(api_key) < 10:
        print("⚠️  OPENAI_API_KEY appears to be a placeholder or too short")
        print("   Please verify your API key is correct")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️  WARNING: OPENAI_API_KEY doesn't start with 'sk-'")
        print("   This may be invalid, but continuing anyway...")
    
    print("✅ .env file found and OPENAI_API_KEY is set")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "openai",
        "python-dotenv",
        "jinja2",
        "python-multipart",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("   Please run: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def check_files():
    """Check if required files exist"""
    required_files = [
        "app_fastapi.py",
        "generate_report.py",
        "generate_cover_letter.py",
        "pdf_resume_parser.py",
        "templates/index.html",
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Missing required files: {', '.join(missing)}")
        return False
    
    print("✅ All required files are present")
    return True

def main():
    """Run all checks"""
    print("🔍 Checking setup...")
    print("-" * 50)
    
    checks = [
        ("Files", check_files),
        ("Dependencies", check_dependencies),
        ("Environment", check_env_file),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        result = check_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All checks passed! You're ready to run the application.")
        print("\nTo start the server, run:")
        print("  python app_fastapi.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

