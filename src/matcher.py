import json
import os
import re

from ai_extractor import extract_job, extract_json
from semantic_matcher import semantic_scores, split_chunks

LOW_SCORE = 0.35
HIGH_SCORE = 0.55
JOB_CACHE = os.path.join("data", "job_requirements.json")

STOPWORDS = {
    "experience", "knowledge", "basic", "strong", "with", "of", "and", "or",
    "in", "for", "using", "skills", "skill", "familiarity", "a", "an", "the",
    "concepts", "programming", "version", "control", "working", "calling",
    "other", "another", "related", "any", "good", "understanding",
    "as", "such", "tools", "tool",
}

DEGREES = {
    "bachelor": r"bachelor|\bb\.?\s?sc\b|\bbs\b|undergraduate",
    "master": r"master|\bm\.?\s?sc\b|\bms\b",
    "phd": r"ph\.?\s?d|doctorate",
}
PROJECT_WORDS = r"intern|training|developed|built|designed|implemented|architected"
YEARS_PATTERN = r"\d+\+?\s*(years?|yrs?)"
CERT_WORDS = r"certif|diploma|licen[sc]e|accredit"
RELATED_TERMS = {
    "git": ["gitlab", "bitbucket", "pull request"],
    "machine learning": ["scikit-learn", "sklearn", "tensorflow", "pytorch",
                         "neural network", "classification model", "deep learning"],
    "nlp": ["natural language", "text classification", "tokeniz"],
    "docker": ["container", "kubernetes"],
}
JUDGE_PROMPT = """You check whether a CV excerpt shows that a candidate meets a job requirement.
Return ONLY valid JSON: {"status": "meets", "evidence": ""}
status must be one of: "meets", "partial", "none".
Rules:
- "meets": the excerpt clearly shows the requirement.
- "partial": the excerpt shows something related but not the full requirement.
- "none": the excerpt does not show it. Never assume or guess.
- evidence: copy the exact words from the excerpt that support your answer (at most 25 words). Use "" when status is "none".

REQUIREMENT:
"""


def build_requirements(job):
    reqs = []

    def add(kind, category, items):
        if isinstance(items, str):
            items = [items] if items else []
        for item in items:
            reqs.append({"text": item, "kind": kind, "category": category})

    add("required", "skill", job.get("required_skills", []))
    add("preferred", "skill", job.get("preferred_skills", []))
    add("required", "experience", job.get("required_experience", ""))
    add("preferred", "experience", job.get("preferred_experience", ""))
    add("required", "education", job.get("education", ""))
    add("required", "language", job.get("required_languages", []))
    add("preferred", "language", job.get("preferred_languages", []))
    add("required", "certification", job.get("required_certifications", []))
    add("preferred", "certification", job.get("preferred_certifications", []))
    return reqs


def key_terms(text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]*", text)
    return [w for w in words if len(w) > 1 and w.lower() not in STOPWORDS]


def term_in(term, chunk):
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
    return re.search(pattern, chunk, re.IGNORECASE) is not None


def keyword_hit(requirement, chunks):
    terms = key_terms(requirement)
    if not terms or len(terms) > 3:
        return None
    for chunk in chunks:
        if all(term_in(t, chunk) for t in terms):
            return chunk
    return None


def partial_hit(requirement, chunks):
    terms = key_terms(requirement)
    if not 2 <= len(terms) <= 4:
        return None
    best, best_n = None, 0
    for chunk in chunks:
        n = sum(1 for t in terms if term_in(t, chunk))
        if n > best_n:
            best, best_n = chunk, n
    return best if best_n >= 2 else None
def related_hit(requirement, chunks):
    req = requirement.lower()
    for key, related in RELATED_TERMS.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", req):
            for chunk in chunks:
                if any(w in chunk.lower() for w in related):
                    return chunk
    return None

def normalize(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def evidence_in_cv(evidence, cv_text):
    ev = normalize(evidence or "")
    return len(ev) >= 4 and ev in normalize(cv_text)


def grounded(req, evidence, score):
    """The quote must actually relate to the requirement, not just exist in the CV."""
    if req["category"] == "certification":
        return re.search(CERT_WORDS, evidence, re.IGNORECASE) is not None
    if any(term_in(t, evidence) for t in key_terms(req["text"])):
        return True
    return score >= HIGH_SCORE


def judge(requirement, matches):
    excerpt = "\n".join("- " + chunk for chunk, _ in matches)
    verdict, _ = extract_json(JUDGE_PROMPT, f"{requirement}\n\nCV EXCERPT:\n{excerpt}")
    return verdict or {}


def degree_level(text):
    t = text.lower()
    if "master" in t:
        return "master"
    if "phd" in t or "ph.d" in t or "doctor" in t:
        return "phd"
    if "bachelor" in t:
        return "bachelor"
    return None


def education_check(req, result, chunks):
    level = degree_level(req["text"])
    if not level:
        return None
    level_re = re.compile(DEGREES[level], re.IGNORECASE)
    fields = []
    parts = re.split(r"\bin\b", req["text"], maxsplit=1)
    if len(parts) == 2:
        for part in re.split(r",|\bor\b", parts[1]):
            part = part.strip(" .")
            if part and "related" not in part.lower():
                fields.append(part)
    degree_chunks = [c for c in chunks if level_re.search(c)]
    if not degree_chunks:
        result["method"] = "no degree found"
        return result
    for c in degree_chunks:
        if not fields or any(term_in(f, c) for f in fields):
            result.update(status="meets", evidence=c, method="degree and field found")
            return result
    result.update(status="partial", evidence=degree_chunks[0],
                  method="degree found, field not confirmed")
    return result


def experience_check(req, result, chunks):
    accepts_projects = re.search(r"intern|project|training", req["text"], re.IGNORECASE)
    pattern = PROJECT_WORDS if accepts_projects else YEARS_PATTERN
    found = [c for c in chunks if re.search(pattern, c, re.IGNORECASE)]
    if not found:
        result["method"] = "no experience evidence"
        return result
    method = ("projects/training found, duration not verified" if accepts_projects
              else "years mentioned, role not verified")
    result.update(status="partial", evidence=max(found, key=len), method=method)
    return result


def match_requirement(req, kw_chunks, cv_text, matches):
    score = round(matches[0][1], 2) if matches else 0.0
    result = {**req, "status": "no_evidence", "evidence": "", "method": "", "score": score}

    if req["category"] == "education":
        checked = education_check(req, result, kw_chunks)
        if checked:
            return checked
    if req["category"] == "experience":
        return experience_check(req, result, kw_chunks)

    hit = keyword_hit(req["text"], kw_chunks)
    if hit:
        result.update(status="meets", evidence=hit, method="keyword")
        return result

    if score >= LOW_SCORE:
        verdict = judge(req["text"], matches)
        status = verdict.get("status")
        evidence = verdict.get("evidence", "")
        if (status in ("meets", "partial") and evidence_in_cv(evidence, cv_text)
                and grounded(req, evidence, score)):
            result.update(status=status, evidence=evidence, method="semantic + AI check")
            return result
        result["method"] = "semantic + AI check, no verified evidence"
    else:
        result["method"] = "low similarity"

    partial = partial_hit(req["text"], kw_chunks)
    if partial:
        result.update(status="partial", evidence=partial, method="some keywords found")
        return result
    related = related_hit(req["text"], kw_chunks) if req["category"] == "skill" else None
    if related:
        result.update(status="partial", evidence=related,
                      method="related term found, not the exact skill")
    return result

def match_cv(job, cv_text):
    reqs = build_requirements(job)
    kw_chunks = split_chunks(cv_text, min_len=4)
    texts = sorted({r["text"] for r in reqs})
    sem = semantic_scores(texts, cv_text, top_k=2)
    return [match_requirement(r, kw_chunks, cv_text, sem.get(r["text"], [])) for r in reqs]


def get_job_requirements(force=False):
    if os.path.exists(JOB_CACHE) and not force:
        with open(JOB_CACHE, encoding="utf-8") as f:
            return json.load(f)
    from job_description import load_job_description

    job, err = extract_job(load_job_description())
    if not job:
        raise RuntimeError(err)
    os.makedirs("data", exist_ok=True)
    with open(JOB_CACHE, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)
    return job


LABELS = {"meets": "MEETS", "partial": "PARTIAL", "no_evidence": "NO EVIDENCE FOUND"}


def summary(results):
    required = [r for r in results if r["kind"] == "required"]
    return ", ".join(
        f"{label.lower()}: {sum(1 for r in required if r['status'] == key)}"
        for key, label in LABELS.items()
    )


if __name__ == "__main__":
    import glob
    from cv_extractor import extract_text

    job = get_job_requirements()
    for path in glob.glob("temp/*.pdf") + glob.glob("temp/*.docx"):
        text, error = extract_text(path)
        print("=" * 40)
        print("CV:", os.path.basename(path))
        if error:
            print("Skipped:", error)
            continue
        results = match_cv(job, text)
        for r in results:
            print(f"[{r['kind'].upper()}] {r['text']}")
            print(f"    -> {LABELS[r['status']]} ({r['method']}, score {r['score']})")
            if r["evidence"]:
                print("    evidence:", r["evidence"][:100])
        print("SUMMARY (required) ->", summary(results))