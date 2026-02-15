import time
import numpy as np
import cv2

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from backend.config import (
    MATCH_CONFIRMATIONS,
    MATCH_STRICT_THRESHOLD,
    MATCH_THRESHOLD,
    SESSION_TTL_SECONDS,
)
from backend.recognizer import recognize_from_frame
from backend.security import require_session
from database.db import (
    delete_dtr_log,
    get_attendance_records,
    get_daily_summary,
    get_teacher_by_id,
    log_dtr_punch,
)

router = APIRouter()

_MATCH_SESSIONS: dict[str, dict[str, float | int]] = {}


def _cleanup_sessions(now: float) -> None:
    expired = [k for k, v in _MATCH_SESSIONS.items() if now - float(v["updated_at"]) > SESSION_TTL_SECONDS]
    for k in expired:
        _MATCH_SESSIONS.pop(k, None)


def _update_session(session_id: str, teacher_id: int, now: float) -> int:
    entry = _MATCH_SESSIONS.get(session_id)
    if entry and int(entry["teacher_id"]) == teacher_id:
        entry["count"] = int(entry["count"]) + 1
        entry["updated_at"] = now
        return int(entry["count"])
    _MATCH_SESSIONS[session_id] = {"teacher_id": teacher_id, "count": 1, "updated_at": now}
    return 1


@router.get("/attendance")
def attendance(date: str | None = None):
    rows = get_attendance_records(date)
    return [
        {
            "id": r[0],
            "full_name": r[1],
            "department": r[2],
            "date": r[3],
            "time_in": r[4],
            "time_out": r[5],
            "status": r[6],
        }
        for r in rows
    ]


@router.get("/attendance/summary")
def summary(date: str):
    return get_daily_summary(date)


@router.post("/attendance/recognize")
async def recognize_attendance(
    _session: dict = Depends(require_session),
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None),
):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Upload JPG/PNG only.")

    data = await file.read()
    img_array = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    teacher_id, conf, reason = recognize_from_frame(frame, threshold=MATCH_THRESHOLD)

    if teacher_id is None:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        return {
            "verified": False,
            "teacher_id": None,
            "confidence": conf,
            "reason": reason or "no_match",
        }

    # Prevent ghost IDs (model predicts an ID not in DB)
    row = get_teacher_by_id(teacher_id)
    if not row:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        return {"verified": False, "teacher_id": teacher_id, "confidence": conf, "reason": "unknown_face"}

    if conf is None or conf > MATCH_STRICT_THRESHOLD:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        return {
            "verified": False,
            "teacher_id": None,
            "confidence": conf,
            "reason": "low_confidence",
        }

    if x_session_id:
        now = time.monotonic()
        _cleanup_sessions(now)
        count = _update_session(x_session_id, teacher_id, now)
        if count < MATCH_CONFIRMATIONS:
            return {
                "verified": False,
                "teacher_id": teacher_id,
                "confidence": conf,
                "reason": "pending_confirmation",
                "count": count,
                "needed": MATCH_CONFIRMATIONS,
            }

    # log DTR (time in/out) for this teacher_id
    result = log_dtr_punch(teacher_id)

    return {
        "verified": True,
        "teacher_id": teacher_id,
        "confidence": conf,
        **result
    }


@router.delete("/attendance/{log_id}")
def delete_attendance(log_id: int, _session: dict = Depends(require_session)):
    ok = delete_dtr_log(log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    return {"ok": True}


