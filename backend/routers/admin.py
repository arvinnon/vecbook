import shutil

from fastapi import APIRouter, Depends, HTTPException

from backend.config import FACES_DIR, MODEL_PATH
from backend.security import require_session
from backend.services.training import reset_training_status
from database.db import clear_all_tables, clear_attendance

router = APIRouter(dependencies=[Depends(require_session)])


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

    # 4) reset training status (optional)
    reset_training_status()

    return {"ok": True, "message": "Reset complete: teachers + faces + model cleared"}

