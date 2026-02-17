import time
from datetime import datetime
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
    AttendanceV2ScanResult,
    delete_attendance_record,
    get_attendance_records,
    get_daily_summary,
    get_teacher_by_id,
    process_attendance_scan_v2,
)

router = APIRouter()

_MATCH_SESSIONS: dict[str, dict[str, float | int]] = {}


def process_recognize_scan_v2_contract(
    *,
    teacher_id: int | None,
    full_name: str | None,
    department: str | None,
    confidence: float | None,
    scan_verified: bool,
    reason: str | None,
    event_date: str,
    event_time: str,
    session_id: str | None,
    request_id: str | None,
) -> AttendanceV2ScanResult:
    """
    Retrofit contract for attendance v2 engine integration.

    Planned usage:
    - /attendance/recognize routes verified/failed scan outcomes through a
      single v2 decision engine in database/db.py (process_attendance_scan_v2).
    """
    return process_attendance_scan_v2(
        teacher_id=teacher_id,
        full_name=full_name,
        department=department,
        confidence=confidence,
        scan_verified=scan_verified,
        reason=reason,
        event_date=event_date,
        event_time=event_time,
        session_id=session_id,
        request_id=request_id,
    )


def _decision_to_legacy_reason(decision_code: str, fallback: str | None = None) -> str | None:
    mapping = {
        "FACE_PENDING_CONFIRMATION": "pending_confirmation",
        "FACE_LOW_CONFIDENCE": "low_confidence",
        "FACE_NO_MATCH": fallback or "no_match",
        "UNKNOWN_FACE_NOT_ENROLLED": "unknown_face",
        "OUTSIDE_SCHEDULE": "out_of_shift",
        "OUTSIDE_SCHEDULE_LUNCH": "lunch_break",
        "DAY_COMPLETE": "day_complete",
        "DUPLICATE_IGNORED": "already_logged",
        "ERROR": "error",
    }
    return mapping.get(decision_code, fallback)


def _legacy_status_for_logged_scan(result: AttendanceV2ScanResult) -> str:
    decision = result["decision_code"]
    if decision == "TIME_OUT_SET":
        return "Recorded"
    if decision == "TIME_IN_SET":
        return "Late" if result["status"] == "Late" else "On-Time"
    return result["status"] or "Logged"


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
def attendance(date: str | None = None, _session: dict = Depends(require_session)):
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
            "last_scan_time": r[7],
        }
        for r in rows
    ]


@router.get("/attendance/summary")
def summary(date: str, _session: dict = Depends(require_session)):
    return get_daily_summary(date)


@router.post("/attendance/recognize")
async def recognize_attendance(
    _session: dict = Depends(require_session),
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Upload JPG/PNG only.")

    data = await file.read()
    img_array = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    now = datetime.now()
    event_date = now.strftime("%Y-%m-%d")
    event_time = now.strftime("%H:%M:%S")

    teacher_id, conf, reason = recognize_from_frame(frame, threshold=MATCH_THRESHOLD)

    if teacher_id is None:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        result = process_recognize_scan_v2_contract(
            teacher_id=None,
            full_name=None,
            department=None,
            confidence=conf,
            scan_verified=False,
            reason=reason or "no_match",
            event_date=event_date,
            event_time=event_time,
            session_id=x_session_id,
            request_id=x_request_id,
        )
        return {
            "verified": False,
            "teacher_id": None,
            "confidence": conf,
            "reason": _decision_to_legacy_reason(result["decision_code"], reason or "no_match"),
            "decision_code": result["decision_code"],
            "scan_event_id": result["scan_event_id"],
        }

    # Prevent ghost IDs (model predicts an ID not in DB)
    row = get_teacher_by_id(teacher_id)
    if not row:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        result = process_recognize_scan_v2_contract(
            teacher_id=teacher_id,
            full_name=None,
            department=None,
            confidence=conf,
            scan_verified=False,
            reason="unknown_face",
            event_date=event_date,
            event_time=event_time,
            session_id=x_session_id,
            request_id=x_request_id,
        )
        return {
            "verified": False,
            "teacher_id": teacher_id,
            "confidence": conf,
            "reason": _decision_to_legacy_reason(result["decision_code"], "unknown_face"),
            "decision_code": result["decision_code"],
            "scan_event_id": result["scan_event_id"],
        }
    teacher_name = row[1]
    teacher_department = row[2]

    if conf is None or conf > MATCH_STRICT_THRESHOLD:
        if x_session_id:
            _MATCH_SESSIONS.pop(x_session_id, None)
        result = process_recognize_scan_v2_contract(
            teacher_id=teacher_id,
            full_name=teacher_name,
            department=teacher_department,
            confidence=conf,
            scan_verified=False,
            reason="low_confidence",
            event_date=event_date,
            event_time=event_time,
            session_id=x_session_id,
            request_id=x_request_id,
        )
        return {
            "verified": False,
            "teacher_id": None,
            "confidence": conf,
            "reason": _decision_to_legacy_reason(result["decision_code"], "low_confidence"),
            "decision_code": result["decision_code"],
            "scan_event_id": result["scan_event_id"],
        }

    if x_session_id:
        now_mono = time.monotonic()
        _cleanup_sessions(now_mono)
        count = _update_session(x_session_id, teacher_id, now_mono)
        if count < MATCH_CONFIRMATIONS:
            result = process_recognize_scan_v2_contract(
                teacher_id=teacher_id,
                full_name=teacher_name,
                department=teacher_department,
                confidence=conf,
                scan_verified=False,
                reason="pending_confirmation",
                event_date=event_date,
                event_time=event_time,
                session_id=x_session_id,
                request_id=x_request_id,
            )
            return {
                "verified": False,
                "teacher_id": teacher_id,
                "full_name": teacher_name,
                "department": teacher_department,
                "confidence": conf,
                "reason": _decision_to_legacy_reason(result["decision_code"], "pending_confirmation"),
                "count": count,
                "needed": MATCH_CONFIRMATIONS,
                "decision_code": result["decision_code"],
                "scan_event_id": result["scan_event_id"],
            }

    result = process_recognize_scan_v2_contract(
        teacher_id=teacher_id,
        full_name=teacher_name,
        department=teacher_department,
        confidence=conf,
        scan_verified=True,
        reason=reason,
        event_date=event_date,
        event_time=event_time,
        session_id=x_session_id,
        request_id=x_request_id,
    )

    if x_session_id and result["decision_code"] in {"TIME_IN_SET", "TIME_OUT_SET", "DAY_COMPLETE"}:
        _MATCH_SESSIONS.pop(x_session_id, None)

    legacy_reason = _decision_to_legacy_reason(result["decision_code"], reason)
    payload = {
        "verified": result["verified"],
        "teacher_id": teacher_id,
        "full_name": teacher_name,
        "department": teacher_department,
        "confidence": conf,
        "logged": result["logged"],
        "date": result["date"],
        "decision_code": result["decision_code"],
        "scan_event_id": result["scan_event_id"],
        "scan_attempts_today": result["scan_attempts_today"],
        "requires_admin_review": result["requires_admin_review"],
        "request_id": result["request_id"],
    }
    if result["late_by_minutes"] is not None:
        payload["late_by_minutes"] = result["late_by_minutes"]
    if result["worked_minutes"] is not None:
        payload["worked_minutes"] = result["worked_minutes"]
    if result["undertime_minutes"] is not None:
        payload["undertime_minutes"] = result["undertime_minutes"]
    if result["auto_closed"]:
        payload["auto_closed"] = True
    if result["logged"]:
        payload["time_in"] = result["event_time"]
        payload["status"] = _legacy_status_for_logged_scan(result)
        payload["slot"] = "time_in" if result["dtr_action"] == "time_in" else "time_out"
        payload["already_complete"] = False
        return payload

    payload["time"] = result["event_time"]
    payload["already_complete"] = result["decision_code"] == "DAY_COMPLETE"
    if legacy_reason:
        payload["reason"] = legacy_reason
    if result["retry_after_seconds"] is not None:
        payload["retry_after_seconds"] = result["retry_after_seconds"]
    return payload


@router.delete("/attendance/{log_id}")
def delete_attendance(log_id: int, _session: dict = Depends(require_session)):
    ok = delete_attendance_record(log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    return {"ok": True}


