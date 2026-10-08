import base64
import os
import re
from gmail_client import get_gmail_service
from email_reader import search_emails, read_email
from processed_store import load_processed_ids, save_processed_ids

TEMP_DIR = "temp"
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def is_supported(filename):
    return os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS


def download_attachment(service, msg_id, attachment):
    data = service.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=attachment["attachment_id"]
    ).execute()
    return base64.urlsafe_b64decode(data["data"])


def save_attachment(msg_id, filename, file_bytes):
    os.makedirs(TEMP_DIR, exist_ok=True)
    safe_name = re.sub(r"[^\w.\- ]", "_", os.path.basename(filename))
    path = os.path.join(TEMP_DIR, f"{msg_id}_{safe_name}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def download_cvs(service, email):
    saved = []
    for att in email["attachments"]:
        if not att["attachment_id"] or not is_supported(att["filename"]):
            print("  Skipped:", att["filename"])
            continue
        file_bytes = download_attachment(service, email["id"], att)
        saved.append(save_attachment(email["id"], att["filename"], file_bytes))
    return saved


def process_new_emails():
    service = get_gmail_service()
    processed = load_processed_ids()
    results = []
    for m in search_emails(service):
        if m["id"] in processed:
            continue
        email = read_email(service, m["id"])
        print("Email from:", email["sender"], "| Subject:", email["subject"])
        try:
            files = download_cvs(service, email)
        except Exception as e:
            print("  Error, will retry next run:", e)
            continue
        if not files:
            print("  No supported CV attached.")
        for f in files:
            print("  Saved:", f)
        results.append({"email": email, "files": files})
        processed.add(m["id"])
    save_processed_ids(processed)
    return results


if __name__ == "__main__":
    process_new_emails()