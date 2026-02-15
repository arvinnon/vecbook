from fastapi import APIRouter, Depends, HTTPException

from backend.config import (
    BLUR_THRESHOLD,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    DB_PATH,
    ENABLE_DEBUG_ENDPOINTS,
    FACE_CENTER_MAX_OFFSET_RATIO,
    MAX_FACES,
    MIN_FACE_SIZE,
    MATCH_CONFIRMATIONS,
    MATCH_STRICT_THRESHOLD,
    MATCH_THRESHOLD,
    SESSION_TTL_SECONDS,
)
from backend.security import require_session

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/debug/dbpath")
def dbpath(_session: dict = Depends(require_session)):
    if not ENABLE_DEBUG_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"db_path": str(DB_PATH)}


@router.get("/config/recognition")
def recognition_config():
    return {
        "match_threshold": MATCH_THRESHOLD,
        "match_strict_threshold": MATCH_STRICT_THRESHOLD,
        "match_confirmations": MATCH_CONFIRMATIONS,
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "max_faces": MAX_FACES,
        "min_face_size": MIN_FACE_SIZE,
        "face_center_max_offset_ratio": FACE_CENTER_MAX_OFFSET_RATIO,
        "blur_threshold": BLUR_THRESHOLD,
        "brightness_min": BRIGHTNESS_MIN,
        "brightness_max": BRIGHTNESS_MAX,
    }
