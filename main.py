# main.py
import io
import re
import datetime
import os
from pathlib import Path
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

# Define the absolute path to the project's base directory
BASE_DIR = Path(__file__).resolve().parent

# Mount the 'static' directory using an absolute path for deployment reliability
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static"
)

# Point to the 'templates' directory using an absolute path
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

print("Loading NLP model...")
# --- CHANGE THE MODEL NAME HERE ---
similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded successfully.")


# --- NLP HELPER FUNCTIONS ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    text = ""
    try:
        if filename.endswith('.pdf'):
            pdf_file = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
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

    # --- Basic Info Extraction ---
    details["email"] = (re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text) or re.search(
        r'E-mail\s*:\s*([\w.+-]+@[\w-]+\.[\w.-]+)', text, re.I)).group(0) if re.search(
        r'[\w.+-]+@[\w-]+\.[\w.-]+', text) else "Not Found"
    details["phone"] = (re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?(\d{3}[-.\s]?\d{4})', text)).group(
        0).strip() if re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?(\d{3}[-.\s]?\d{4})', text) else "Not Found"

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # --- Name Extraction ---
    if lines:
        potential_name = lines[0]
        if len(potential_name.split()) < 5 and '@' not in potential_name and not any(
                char.isdigit() for char in potential_name):
            details["name"] = potential_name.title()

    if details["name"] == "Not Found" and details["email"] != "Not Found":
        username = details["email"].split('@')[0]
        name_from_email = re.sub(r'\d+', '', username)
        name_from_email = re.sub(r'[\._-]', ' ', name_from_email)
        details["name"] = name_from_email.strip().upper()
        if not details["name"]:
            details["name"] = "Not Found"

    # --- Skills Extraction ---
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

    # --- Education Extraction ---
    education_details = "Not Found"
    degrees_pattern = r'\b(B\.?Tech|B\.?E\.?|M\.?S\.?|B\.?Sc|M\.?Sc|BBA|MBA|MCA|Ph\.?D|Bachelor[’\']?s?\s*of|Master[’\']?s?\s*of|Doctor of Philosophy)\b'
    institution_keywords = ['University', 'College', 'Institute', 'School', 'Academy']
    institution_pattern = r'\b(' + '|'.join(institution_keywords) + r')\b'

    education_found = False
    for i, line in enumerate(lines):
        if re.search(institution_pattern, line, re.I):
            context_lines = [lines[i - 1], line] if i > 0 else [line]
            full_detail = " ".join(context_lines)

            if re.search(degrees_pattern, full_detail, re.I):
                education_details = re.sub(r'\s+', ' ', full_detail).strip()
                education_found = True
                break

    if not education_found:
        for line in lines:
            if re.search(degrees_pattern, line, re.I):
                education_details = re.sub(r'\s+', ' ', line).strip()
                break
    details["education"] = education_details

    # --- Experience Calculation ---
    month_map = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
        'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }
    month_regex = r'(' + '|'.join(month_map.keys()) + r')'
    date_range_regex = re.compile(
        r'(?i)' + month_regex + r'\s+(\d{4})\s*[-–to]+\s*(?:(' + month_regex + r')\s+(\d{4})|(present|current|till date))',
        re.IGNORECASE
    )

    date_ranges = date_range_regex.findall(text)
    total_months = 0
    now = datetime.datetime.now()

    if date_ranges:
        for match in date_ranges:
            try:
                start_month = month_map[match[0].lower()]
                start_year = int(match[1])
                end_month_str, end_year_str, present_keyword = match[3], match[4], match[5]

                if present_keyword:
                    end_month, end_year = now.month, now.year
                elif end_month_str and end_year_str:
                    end_month, end_year = month_map[end_month_str.lower()], int(end_year_str)
                else:
                    continue

                duration = (end_year - start_year) * 12 + (end_month - start_month) + 1
                if duration > 0:
                    total_months += duration
            except (KeyError, ValueError):
                continue

    if total_months > 0:
        years = total_months // 12
        months = total_months % 12
        exp_str = ""
        if years > 0:
            exp_str += f"{years} year{'s' if years > 1 else ''}"
        if months > 0:
            if exp_str:
                exp_str += " and "
            exp_str += f"{months} month{'s' if months > 1 else ''}"
        details["experience"] = exp_str
    else:
        details["experience"] = "Amateur"

    return details


# --- API ENDPOINTS ---
@app.get("/health", status_code=200)
async def health_check():
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
        if not resume_text.strip():
            continue

        cosine_score = util.cos_sim(similarity_model.encode(resume_text, convert_to_tensor=True),
                                    jd_embedding).item()
        extracted_details = extract_resume_details_lightweight(resume_text)

        ranked_candidates.append({
            "filename": resume.filename,
            "score": round(max(0, cosine_score) * 100, 2),
            "details": extracted_details
        })

    ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
    return JSONResponse(content={"candidates": ranked_candidates})