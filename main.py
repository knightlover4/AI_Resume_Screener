# main.py
import io
import re
from typing import List

import docx
from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer, util
import pypdf

# --- INITIALIZATION ---
app = FastAPI(title="AI Resume Screener")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

print("Loading NLP model...")
# --- CHANGE THE MODEL NAME HERE ---
similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded successfully.")

# --- NLP HELPER FUNCTIONS ---
# (The rest of your helper functions remain the same)
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    text = ""
    try:
        if filename.endswith('.pdf'):
            pdf_file = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            text = "".join(page.extract_text() for page in reader.pages)
        elif filename.endswith('.docx'):
            doc_file = io.BytesIO(file_content)
            document = docx.Document(doc_file)
            text = "\n".join(para.text for para in document.paragraphs)
    except Exception as e:
        print(f"Error parsing file {filename}: {e}")
    return text

def extract_resume_details_lightweight(text: str) -> dict:
    details = {
        "name": "Not Found", "email": "Not Found", "phone": "Not Found",
        "education": "Not Found", "experience": "Not Found", "skills": []
    }
    details["email"] = (re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text) or re.search(r'E-mail\s*:\s*([\w.+-]+@[\w-]+\.[\w.-]+)', text, re.I)).group(0) if re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text) else "Not Found"
    details["phone"] = (re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?(\d{3}[-.\s]?\d{4})', text)).group(0).strip() if re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?(\d{3}[-.\s]?\d{4})', text) else "Not Found"
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        potential_name = lines[0]
        if len(potential_name.split()) < 5:
            details["name"] = potential_name
    if details["name"] == "Not Found" and details["email"] != "Not Found":
        details["name"] = details["email"].split('@')[0].replace('.', ' ').replace('_', ' ').title()
    SKILLS_LIST = [
        'python', 'java', 'c++', 'javascript', 'sql', 'pandas', 'numpy', 'scikit-learn',
        'tensorflow', 'pytorch', 'keras', 'nlp', 'streamlit', 'flask', 'fastapi',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'react', 'vue', 'angular',
        'data structures', 'algorithms', 'deep learning', 'machine learning'
    ]
    found_skills = set()
    for skill in SKILLS_LIST:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            found_skills.add(skill.title())
    details["skills"] = list(found_skills)
    education_pattern = r"(?i)(education|university|college|b\.tech|bachelor of technology|b\.e|bachelor of engineering|m\.s|master of science|ph\.d)[\s:]*([^\n]+)"
    edu_match = re.search(education_pattern, text)
    if edu_match:
        details["education"] = edu_match.group(2).strip()
    else:
        details["education"] = "Not Found"
    experience_match = re.search(r'(?i)(experience|work history|employment).*', text)
    if experience_match:
        details["experience"] = experience_match.group(0).split('\n')[0][:100]
    return details


# --- API ENDPOINTS ---

# --- THIS IS THE NEW HEALTH CHECK ENDPOINT ---
@app.get("/health", status_code=200)
async def health_check():
    """A lightweight endpoint for Render's health checks."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/rank_resumes/")
async def rank_resumes(
    job_description: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    if not job_description or not resumes:
        return JSONResponse(status_code=400, content={"error": "Job description and at least one resume must be provided."})
    try:
        jd_embedding = similarity_model.encode(job_description, convert_to_tensor=True)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to process job description: {e}"})
    
    ranked_candidates = []
    for resume in resumes:
        resume_content = await resume.read()
        resume_text = extract_text_from_file(resume_content, resume.filename)
        if not resume_text.strip(): continue
        
        cosine_score = util.cos_sim(similarity_model.encode(resume_text, convert_to_tensor=True), jd_embedding).item()
        extracted_details = extract_resume_details_lightweight(resume_text)
        
        ranked_candidates.append({
            "filename": resume.filename,
            "score": round(max(0, cosine_score) * 100, 2),
            "details": extracted_details
        })

    ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
    return JSONResponse(content={"candidates": ranked_candidates})