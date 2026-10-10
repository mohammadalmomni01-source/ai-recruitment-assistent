import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from matcher import LABELS, match_cv

CV = """JANE DOE
Backend Developer | Amman, Jordan

EXPERIENCE
- Built web services that expose JSON endpoints for a mobile app.
- Managed source code on GitLab using feature branches and pull requests.
- Packaged applications into containers and deployed them with CI pipelines.
- Trained classification models with scikit-learn to predict customer churn.

EDUCATION
BSc in Software Engineering, University of Jordan, 2021

LANGUAGES
English: Professional; Arabic: Native
"""

JOB = {
    "required_skills": [
        "Experience calling REST APIs and working with JSON",
        "Git and GitHub for version control",
        "Basic knowledge of machine learning or NLP concepts",
        "Strong Python programming",
    ],
    "preferred_skills": ["Familiarity with Docker"],
    "education": "Bachelor's degree in Computer Science, Software Engineering or a related field",
    "required_languages": ["English"],
}

if __name__ == "__main__":
    for r in match_cv(JOB, CV):
        print(f"[{r['kind'].upper()}] {r['text']}")
        print(f"    -> {LABELS[r['status']]} ({r['method']}, score {r['score']})")
        if r["evidence"]:
            print("    evidence:", r["evidence"][:100])