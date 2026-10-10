import glob
import json
import os
import ollama
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

JOB_PROMPT = """You extract structured information from a job description.
Return ONLY valid JSON with exactly these keys:
{
  "job_title": "",
  "required_skills": [],
  "preferred_skills": [],
  "required_experience": "",
  "preferred_experience": "",
  "education": "",
  "languages": [],
  "certifications": []
}
Rules:
- Use only information that appears in the text.
- If something is not mentioned, use "" for strings or [] for lists.
- Do not add explanations.

JOB DESCRIPTION:
"""

CV_PROMPT = """You extract structured information from a candidate's CV.
Return ONLY valid JSON with exactly these keys:
{
  "name": "",
  "skills": [],
  "work_experience": [{"title": "", "company": "", "duration": "", "description": ""}],
  "education": [{"degree": "", "institution": "", "year": ""}],
  "languages": [],
  "certifications": []
}
Rules:
- Use only information that appears in the CV. Never invent skills, jobs or degrees.
- If something is not mentioned, use "" for strings or [] for lists.
- Do not add explanations.

CV TEXT:
"""


def ask_llm(prompt, text):
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt + text}],
        format="json",
        options={"temperature": 0},
    )
    return response["message"]["content"]


def extract_json(prompt, text, retries=2):
    last_error = None
    for _ in range(retries + 1):
        try:
            return json.loads(ask_llm(prompt, text)), None
        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON from model: {e}"
        except Exception as e:
            return None, f"Ollama error: {e}"
    return None, last_error


def extract_job(jd_text):
    return extract_json(JOB_PROMPT, jd_text)


def extract_candidate(cv_text):
    return extract_json(CV_PROMPT, cv_text)


if __name__ == "__main__":
    from job_description import load_job_description
    from cv_extractor import extract_text

    job, err = extract_job(load_job_description())
    print("JOB REQUIREMENTS:")
    print(json.dumps(job, indent=2) if job else err)

    for path in glob.glob("temp/*.pdf") + glob.glob("temp/*.docx"):
        text, error = extract_text(path)
        print("=" * 40)
        print("CV:", os.path.basename(path))
        if error:
            print("Skipped:", error)
            continue
        candidate, err = extract_candidate(text)
        print(json.dumps(candidate, indent=2) if candidate else err)