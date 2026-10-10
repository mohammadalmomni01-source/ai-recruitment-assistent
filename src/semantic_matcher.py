import re
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def split_chunks(text, min_len=15):
    """Split CV text into short sentence-sized pieces."""
    chunks = []
    for line in text.split("\n"):
        for part in re.split(r"(?<=[.!?])\s+|\s*\|\s*", line):
            part = part.strip(" -\u2022\t")
            if len(part) >= min_len:
                chunks.append(part)
    return chunks


def best_matches(requirement, chunks, chunk_embeddings, top_k=2):
    req_embedding = get_model().encode(requirement, convert_to_tensor=True)
    scores = util.cos_sim(req_embedding, chunk_embeddings)[0]
    top = scores.topk(min(top_k, len(chunks)))
    return [
        (chunks[int(i)], float(s))
        for s, i in zip(top.values, top.indices)
    ]


def semantic_scores(requirements, cv_text, top_k=2):
    """For each requirement, return the best matching CV pieces with similarity scores."""
    chunks = split_chunks(cv_text)
    if not chunks:
        return {r: [] for r in requirements}
    embeddings = get_model().encode(chunks, convert_to_tensor=True)
    return {r: best_matches(r, chunks, embeddings, top_k) for r in requirements}


if __name__ == "__main__":
    import glob
    import os
    from cv_extractor import extract_text

    requirements = [
        "Strong Python programming",
        "Experience calling REST APIs and working with JSON",
        "Git and GitHub for version control",
        "Basic knowledge of machine learning or NLP concepts",
        "Experience with SQL or another database",
        "Familiarity with Docker",
        "Knowledge of embeddings and vector search",
    ]

    for path in glob.glob("temp/*.pdf") + glob.glob("temp/*.docx"):
        text, error = extract_text(path)
        print("=" * 40)
        print("CV:", os.path.basename(path))
        if error:
            print("Skipped:", error)
            continue
        for req, matches in semantic_scores(requirements, text).items():
            print("-", req)
            for chunk, score in matches[:1]:
                print(f"    {score:.2f}  {chunk[:90]}")