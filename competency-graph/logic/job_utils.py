import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AMETID_FILE = BASE_DIR / "ametikohad.json"

def load_jobs():
    """
     Load job entries from the ametikohad.json file.
     """
    if AMETID_FILE.exists():
        with AMETID_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_jobs(jobs):
    """
       Save a list of job entries to the ametikohad.json file.
       """
    with AMETID_FILE.open("w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)