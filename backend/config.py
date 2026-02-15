import os
import secrets
from datetime import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

ASSETS_DIR = Path(os.getenv("VECBOOK_ASSETS_DIR", BASE_DIR / "assets"))
FACES_DIR = Path(os.getenv("VECBOOK_FACES_DIR", ASSETS_DIR / "faces"))
MODEL_PATH = Path(os.getenv("VECBOOK_MODEL_PATH", BASE_DIR / "face_recognition" / "face_model.yml"))
DB_PATH = Path(os.getenv("VECBOOK_DB_PATH", BASE_DIR / "database" / "vecbook.db"))
DEVICE_SECRET = os.getenv("VECBOOK_DEVICE_SECRET", "vecbook-device-secret-change-me").strip()
SIGNING_KEY = (
    os.getenv("VECBOOK_SIGNING_KEY", "").strip()
    or DEVICE_SECRET
    or secrets.token_urlsafe(32)
)
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("VECBOOK_AUTH_TOKEN_TTL_SECONDS", "43200"))


def _parse_bool(value: str | None, fallback: bool) -> bool:
    if value is None:
        return fallback
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _parse_csv(value: str | None, fallback: list[str]) -> list[str]:
    if not value:
        return fallback
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or fallback


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


CORS_ALLOW_ORIGINS = _parse_csv(
    os.getenv("VECBOOK_CORS_ALLOW_ORIGINS"),
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_METHODS = _parse_csv(
    os.getenv("VECBOOK_CORS_ALLOW_METHODS"),
    ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
CORS_ALLOW_HEADERS = _parse_csv(
    os.getenv("VECBOOK_CORS_ALLOW_HEADERS"),
    ["Authorization", "Content-Type", "Accept"],
)
CORS_ALLOW_CREDENTIALS = _parse_bool(os.getenv("VECBOOK_CORS_ALLOW_CREDENTIALS"), True)
ENABLE_DEBUG_ENDPOINTS = _parse_bool(os.getenv("VECBOOK_ENABLE_DEBUG_ENDPOINTS"), False)


AM_START = _parse_time(os.getenv("VECBOOK_AM_START"), time(7, 30))
AM_END = _parse_time(os.getenv("VECBOOK_AM_END"), time(12, 0))
PM_START = _parse_time(os.getenv("VECBOOK_PM_START"), time(13, 0))
PM_END = _parse_time(os.getenv("VECBOOK_PM_END"), time(17, 0))

MATCH_THRESHOLD = float(os.getenv("VECBOOK_MATCH_THRESHOLD", "60"))
MATCH_STRICT_THRESHOLD = float(
    os.getenv("VECBOOK_STRICT_MATCH_THRESHOLD", f"{MATCH_THRESHOLD * 0.85:.2f}")
)
MATCH_CONFIRMATIONS = int(os.getenv("VECBOOK_MATCH_CONFIRMATIONS", "2"))
SESSION_TTL_SECONDS = int(os.getenv("VECBOOK_SESSION_TTL_SECONDS", "10"))

# Recognition gates (reduce false positives)
MAX_FACES = int(os.getenv("VECBOOK_MAX_FACES", "1"))
MIN_FACE_SIZE = int(os.getenv("VECBOOK_MIN_FACE_SIZE", "120"))
FACE_CENTER_MAX_OFFSET_RATIO = float(os.getenv("VECBOOK_FACE_CENTER_MAX_OFFSET_RATIO", "0.35"))
BLUR_THRESHOLD = float(os.getenv("VECBOOK_BLUR_THRESHOLD", "40"))
BRIGHTNESS_MIN = float(os.getenv("VECBOOK_BRIGHTNESS_MIN", "40"))
BRIGHTNESS_MAX = float(os.getenv("VECBOOK_BRIGHTNESS_MAX", "200"))
