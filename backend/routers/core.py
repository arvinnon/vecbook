from fastapi import APIRouter, Depends, HTTPException

from backend.config import (
    ATTENDANCE_ABSENCE_CUTOFF,
    ATTENDANCE_AUTO_CLOSE_CUTOFF,
    ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS,
    ATTENDANCE_GRACE_MINUTES,
    AM_END,
    AM_START,
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
    PM_END,
    PM_START,
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
        "am_start": AM_START.strftime("%H:%M:%S"),
        "am_end": AM_END.strftime("%H:%M:%S"),
        "pm_start": PM_START.strftime("%H:%M:%S"),
        "pm_end": PM_END.strftime("%H:%M:%S"),
        "attendance_grace_minutes": ATTENDANCE_GRACE_MINUTES,
        "attendance_auto_close_cutoff": ATTENDANCE_AUTO_CLOSE_CUTOFF.strftime("%H:%M:%S"),
        "attendance_absence_cutoff": ATTENDANCE_ABSENCE_CUTOFF.strftime("%H:%M:%S"),
        "attendance_duplicate_cooldown_seconds": ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS,
    }
