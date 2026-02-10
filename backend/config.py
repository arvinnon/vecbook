import os
from datetime import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

ASSETS_DIR = Path(os.getenv("VECBOOK_ASSETS_DIR", BASE_DIR / "assets"))
FACES_DIR = Path(os.getenv("VECBOOK_FACES_DIR", ASSETS_DIR / "faces"))
MODEL_PATH = Path(os.getenv("VECBOOK_MODEL_PATH", BASE_DIR / "face_recognition" / "face_model.yml"))
DB_PATH = Path(os.getenv("VECBOOK_DB_PATH", BASE_DIR / "database" / "vecbook.db"))
API_KEY = os.getenv("VECBOOK_API_KEY")


def _parse_time(value: str | None, fallback: time) -> time:
    if not value:
        return fallback
    parts = value.split(":")
    try:
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        ss = int(parts[2]) if len(parts) > 2 else 0
        return time(hh, mm, ss)
    except Exception:
        return fallback


AM_START = _parse_time(os.getenv("VECBOOK_AM_START"), time(7, 30))
AM_END = _parse_time(os.getenv("VECBOOK_AM_END"), time(12, 0))
PM_START = _parse_time(os.getenv("VECBOOK_PM_START"), time(13, 0))
PM_END = _parse_time(os.getenv("VECBOOK_PM_END"), time(17, 0))

MATCH_THRESHOLD = float(os.getenv("VECBOOK_MATCH_THRESHOLD", "60"))
MATCH_CONFIRMATIONS = int(os.getenv("VECBOOK_MATCH_CONFIRMATIONS", "2"))
SESSION_TTL_SECONDS = int(os.getenv("VECBOOK_SESSION_TTL_SECONDS", "10"))
