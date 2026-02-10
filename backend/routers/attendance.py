import numpy as np
import cv2

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.recognizer import recognize_from_frame
from backend.security import require_api_key
from database.db import (
    delete_dtr_log,
    get_attendance_records,
    get_daily_summary,
    get_teacher_by_id,
    log_dtr_punch,
)

router = APIRouter()


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
async def recognize_attendance(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Upload JPG/PNG only.")

    data = await file.read()
    img_array = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    teacher_id, conf = recognize_from_frame(frame, threshold=60.0)

    if teacher_id is None:
        return {"verified": False, "teacher_id": None, "confidence": conf, "reason": "no_match"}

    # Prevent ghost IDs (model predicts an ID not in DB)
    row = get_teacher_by_id(teacher_id)
    if not row:
        return {"verified": False, "teacher_id": teacher_id, "confidence": conf, "reason": "unknown_face"}

    # log DTR (time in/out) for this teacher_id
    result = log_dtr_punch(teacher_id)

    return {
        "verified": True,
        "teacher_id": teacher_id,
        "confidence": conf,
        **result
    }


@router.delete("/attendance/{log_id}")
def delete_attendance(log_id: int, _auth: None = Depends(require_api_key)):
    ok = delete_dtr_log(log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    return {"ok": True}
