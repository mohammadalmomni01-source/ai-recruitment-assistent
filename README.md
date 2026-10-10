# AI Recruitment Screening Assistant

Helps HR screen CVs received by Gmail. It reads a job description, extracts the requirements with a local LLM (Ollama), downloads CVs from email attachments, and compares each CV with each requirement. It does not make hiring decisions: every result comes with evidence from the CV so HR can decide.

## Setup
1. Install Python 3.13, Git, and Ollama, then run `ollama pull llama3.2`.
2. Create and activate a virtual environment, then run `pip install -r requirements.txt`.
3. In Google Cloud, enable the Gmail API, create a Desktop OAuth client, and save it as `credentials.json` in the project root.
4. Create a `.env` file with these lines:

    GMAIL_CREDENTIALS_PATH=credentials.json
    GMAIL_TOKEN_PATH=token.json
    OLLAMA_MODEL=llama3.2
    JOB_SUBJECT_KEYWORD=application

## Run
    python src/gmail_client.py     # test the Gmail login
    python src/email_reader.py     # list application emails
    python src/cv_downloader.py    # download CV attachments to temp/
    python src/cv_extractor.py     # extract text from CVs
    python src/ai_extractor.py     # extract requirements and CV details
    python src/matcher.py          # compare CVs with the job
    python tests/matching.py  # test matching with different wording

## How matching works
Each job requirement gets one result: MEETS, PARTIAL, or NO EVIDENCE FOUND.
1. Rule checks: keywords, degree and field, languages.
2. Embedding similarity (all-MiniLM-L6-v2) finds the closest CV lines.
3. The LLM judges only those lines and must quote the CV. The quote is checked against the CV text, so nothing is assumed.

## Limitations
- A small local model can make mistakes, so results are for HR to review.
- Years of experience are not calculated from date ranges.
- Scanned (image-only) CVs have no extractable text.