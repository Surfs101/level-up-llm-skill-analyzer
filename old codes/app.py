from flask import Flask, request, jsonify, render_template
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Simple HTML form for file upload
HTML_FORM = '''
<!DOCTYPE html>
<html>
<head>
    <title>Skill Gap Analyzer</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        textarea, input { width: 100%; margin: 10px 0; padding: 10px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .result { background: white; padding: 20px; margin-top: 20px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🎯 Skill Gap Analyzer</h1>
    <div class="container">
        <form id="uploadForm">
            <h3>📄 Upload Resume (PDF)</h3>
            <input type="file" name="resume" accept=".pdf" required>
            
            <h3>📝 Paste Job Description</h3>
            <textarea name="job_description" rows="6" placeholder="Paste the job description here..." required></textarea>
            
            <button type="submit">Analyze Skills</button>
        </form>
    </div>
    
    <div id="result" class="result" style="display:none;"></div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '🔄 Analyzing...';
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                let html = `<h2>📊 Analysis Results</h2>`;
                html += `<h3>Fit Score: ${data.fit_score}%</h3>`;
                
                html += `<h4>✅ Your Skills:</h4><ul>`;
                data.matched_skills.forEach(skill => html += `<li>${skill}</li>`);
                html += `</ul>`;
                
                html += `<h4>❌ Skills to Learn:</h4><ul>`;
                data.missing_skills.forEach(skill => html += `<li>${skill}</li>`);
                html += `</ul>`;
                
                html += `<h4>📚 Recommended Courses:</h4>`;
                Object.entries(data.courses).forEach(([skill, courseList]) => {
                    if (courseList && courseList.length > 0) {
                        html += `<p><strong>${skill}:</strong> ${courseList[0].title} (${courseList[0].platform})</p>`;
                    }
                });
                
                html += `<h4>💡 Project Ideas:</h4>`;
                Object.entries(data.projects).forEach(([skill, projectList]) => {
                    if (projectList && projectList.length > 0) {
                        html += `<p><strong>${skill}:</strong> ${projectList[0].title} (${projectList[0].difficulty})</p>`;
                    }
                });
                
                resultDiv.innerHTML = html;
                
            } catch (error) {
                resultDiv.innerHTML = '❌ Error analyzing files. Please try again.';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return HTML_FORM

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get uploaded files and data
        resume_file = request.files.get('resume')
        job_description = request.form.get('job_description', '')
        
        # For demo purposes, we'll use your existing JSON data
        # In a real app, you would process the uploaded files here
        
        # Load your existing analysis data
        with open('final_report.json', 'r') as f:
            final_report = json.load(f)
        
        # Extract the data we need for the frontend
        result = {
            'fit_score': final_report['skill_analysis']['fit_score'],
            'matched_skills': final_report['skill_analysis']['matched_skills'],
            'missing_skills': final_report['skill_analysis']['missing_skills'],
            'courses': final_report['recommendations']['courses'],
            'projects': final_report['recommendations']['projects']
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/report')
def api_report():
    try:
        with open('final_report.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"error": "Run report_preview.ipynb first"})

if __name__ == '__main__':
    print("🚀 Starting Skill Gap Analyzer...")
    print("📊 Go to: http://localhost:5000")
    app.run(debug=True, port=5000)
