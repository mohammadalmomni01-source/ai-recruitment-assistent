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
  "required_languages": [],
  "preferred_languages": [],
  "required_certifications": [],
  "preferred_certifications": []
}
Rules:
- Use only information that appears in the text.
- Keep required and preferred items in separate lists. Never mix them.
- One short item per list entry.
- For required_experience, preferred_experience and education, copy the requirement as written, including qualifiers such as "including internships".
- If a certification is described as preferred, put it in preferred_certifications. If none are required, required_certifications is [].
- If something is not mentioned or says "none", use "" for strings or [] for lists. Never put an empty string or the word "none" inside a list.
- Do not add explanations.

JOB DESCRIPTION:
"""

CV_PROMPT = """You extract structured information from a candidate's CV.
Return ONLY valid JSON with exactly these keys:
{
  "name": "",
  "skills": [],
  "work_experience": [{"title": "", "company": "", "duration": "", "description": ""}],
  "projects": [{"name": "", "description": ""}],
  "education": [{"degree": "", "institution": "", "year": ""}],
  "languages": [],
  "certifications": []
}
Rules:
- Use only information that appears in the CV. Never invent skills, jobs or degrees.
- skills: one skill or tool per list entry, short (for example "Python"). Do not use category labels such as "Programming Languages:".
- work_experience: only real jobs, internships or practical training where the CV names an employer or gives dates. Never create an entry from the headline or title line at the top of the CV. If there are none, use [].
- In work_experience, "title" is the position held, "company" is the employer, and "duration" is only dates or a time period such as "Jun 2025 - Aug 2025" or "3 months". If the CV gives no dates, use "". A university is not an employer, and a project type is not a duration.
- projects: academic, graduation and personal projects go here, not in work_experience. Give each project a short name and a one-sentence description taken from the CV.
- languages: spoken languages only (for example English), not programming languages.
- certifications: only certifications the CV names. If none, use [].
- If something is not mentioned, use "" for strings or [] for lists.
- Do not add explanations.

CV TEXT:
"""


def is_empty(value):
    if value in ("", None, [], {}):
        return True
    if isinstance(value, dict):
        return all(is_empty(v) for v in value.values())
    return False


def remove_empty(value):
    if isinstance(value, list):
        cleaned = [remove_empty(v) for v in value]
        return [v for v in cleaned if not is_empty(v)]
    if isinstance(value, dict):
        return {k: remove_empty(v) for k, v in value.items()}
    return value


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
            return remove_empty(json.loads(ask_llm(prompt, text))), None
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
    print(json.dumps(job, indent=2, ensure_ascii=False) if job else err)

    for path in glob.glob("temp/*.pdf") + glob.glob("temp/*.docx"):
        text, error = extract_text(path)
        print("=" * 40)
        print("CV:", os.path.basename(path))
        if error:
            print("Skipped:", error)
            continue
        candidate, err = extract_candidate(text)
        print(json.dumps(candidate, indent=2, ensure_ascii=False) if candidate else err)