import base64
import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service
from processed_store import load_processed_ids, save_processed_ids

load_dotenv()
JOB_KEYWORD = os.getenv("JOB_SUBJECT_KEYWORD", "application")
QUERY = f'subject:"{JOB_KEYWORD}" has:attachment (filename:pdf OR filename:docx)'


def search_emails(service, query=QUERY, max_results=10):
    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    return result.get("messages", [])


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def get_body(payload):
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        text = get_body(part)
        if text:
            return text
    return ""


def get_attachments(payload):
    found = []
    for part in payload.get("parts", []):
        if part.get("filename"):
            found.append({
                "filename": part["filename"],
                "mime_type": part["mimeType"],
                "attachment_id": part["body"].get("attachmentId"),
            })
        found.extend(get_attachments(part))
    return found


def read_email(service, msg_id):
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()
    payload = msg["payload"]
    headers = payload["headers"]
    return {
        "id": msg_id,
        "sender": get_header(headers, "From"),
        "subject": get_header(headers, "Subject"),
        "body": get_body(payload),
        "attachments": get_attachments(payload),
    }


if __name__ == "__main__":
    service = get_gmail_service()
    processed = load_processed_ids()
    messages = search_emails(service)
    new_messages = [m for m in messages if m["id"] not in processed]
    print(f"Found {len(messages)} matching emails, {len(new_messages)} new")
    for m in new_messages:
        email = read_email(service, m["id"])
        print("-" * 40)
        print("From:", email["sender"])
        print("Subject:", email["subject"])
        print("Attachments:", [a["filename"] for a in email["attachments"]])
        processed.add(m["id"])
    save_processed_ids(processed)