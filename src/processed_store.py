import json
import os

PROCESSED_PATH = os.path.join("data", "processed_ids.json")


def load_processed_ids():
    if not os.path.exists(PROCESSED_PATH):
        return set()
    try:
        with open(PROCESSED_PATH, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_processed_ids(ids):
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    with open(PROCESSED_PATH, "w") as f:
        json.dump(sorted(ids), f, indent=2)