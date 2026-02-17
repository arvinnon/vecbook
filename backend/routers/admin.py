import shutil
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import FACES_DIR, MODEL_PATH
from backend.recognizer import reload_model
from backend.security import require_session
from backend.services.training import reset_training_status
from database.db import (
    DecisionCode,
    clear_all_tables,
    clear_attendance,
    get_scan_events_total_v2,
    get_scan_events_v2,
    run_attendance_maintenance_v2,
)

router = APIRouter(dependencies=[Depends(require_session)])
ALLOWED_DECISION_CODES: set[str] = {
    "TIME_IN_SET",
    "TIME_OUT_SET",
    "AUTO_CLOSED_SET",
    "ABSENCE_MARKED",
    "OUTSIDE_SCHEDULE",
    "OUTSIDE_SCHEDULE_LUNCH",
    "DAY_COMPLETE",
    "FACE_PENDING_CONFIRMATION",
    "FACE_LOW_CONFIDENCE",
    "FACE_NO_MATCH",
    "UNKNOWN_FACE_NOT_ENROLLED",
    "DUPLICATE_IGNORED",
    "ERROR",
}


@router.post("/admin/reset/attendance")
def reset_attendance():
    ok = clear_attendance()
    if not ok:
        raise HTTPException(status_code=400, detail="Attendance table not found. Check DB schema.")
    return {"ok": True, "message": "Attendance logs cleared"}


@router.post("/admin/reset/hard")
def reset_hard():
    # 1) clear DB
    clear_all_tables()

    # 2) delete face images
    faces_dir = FACES_DIR
    if faces_dir.exists():
        shutil.rmtree(faces_dir)
    faces_dir.mkdir(parents=True, exist_ok=True)

    # 3) delete model
    if MODEL_PATH.exists():
        MODEL_PATH.unlink()
    # reset in-memory recognizer cache to match filesystem state
    reload_model()

    # 4) reset training status (optional)
    reset_training_status()

    return {"ok": True, "message": "Reset complete: teachers + faces + model cleared"}


@router.get("/admin/scan-events")
def list_scan_events(
    teacher_id: int | None = None,
    date: str | None = None,
    decision_code: str | None = None,
    requires_review: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    clean_decision = decision_code.strip() if decision_code else None
    if clean_decision and clean_decision not in ALLOWED_DECISION_CODES:
        raise HTTPException(status_code=400, detail="Invalid decision_code filter.")

    typed_decision = cast(DecisionCode | None, clean_decision)
    rows = get_scan_events_v2(
        teacher_id=teacher_id,
        date=date,
        decision_code=typed_decision,
        requires_review=requires_review,
        limit=limit,
        offset=offset,
    )
    total = get_scan_events_total_v2(
        teacher_id=teacher_id,
        date=date,
        decision_code=typed_decision,
        requires_review=requires_review,
    )
    return {
        "rows": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/admin/attendance/maintenance")
def run_attendance_maintenance():
    stats = run_attendance_maintenance_v2()
    return {
        "ok": True,
        "message": "Attendance maintenance completed.",
        **stats,
    }

