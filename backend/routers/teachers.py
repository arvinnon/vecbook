import shutil
import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import FACES_DIR
from backend.security import require_session
from backend.services.training import schedule_training
from database.db import (
    add_teacher,
    get_all_teachers,
    get_teacher_by_id,
    get_teacher_dtr_month,
)

router = APIRouter()


class TeacherCreate(BaseModel):
    full_name: str
    department: str
    employee_id: str


@router.get("/teachers")
def teachers():
    rows = get_all_teachers()
    return [
        {
            "id": r[0],
            "full_name": r[1],
            "department": r[2],
            "employee_id": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


@router.get("/teachers/{teacher_id}")
def teacher_detail(teacher_id: int):
    row = get_teacher_by_id(teacher_id)
    if not row:
        return {"found": False}
    return {
        "found": True,
        "id": row[0],
        "full_name": row[1],
        "department": row[2],
        "employee_id": row[3],
    }


@router.post("/teachers")
def create_teacher(payload: TeacherCreate, _session: dict = Depends(require_session)):
    full_name = payload.full_name.strip()
    department = payload.department.strip()
    employee_id = payload.employee_id.strip()

    if not full_name or not department or not employee_id:
        raise HTTPException(status_code=400, detail="All fields are required.")

    try:
        new_id = add_teacher(full_name, department, employee_id)
        return {
            "id": new_id,
            "full_name": full_name,
            "department": department,
            "employee_id": employee_id,
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Employee ID already exists.")


# Save uploaded face images to assets/faces/<teacher_id>/
@router.post("/teachers/{teacher_id}/faces")
async def upload_faces(
    teacher_id: int,
    background_tasks: BackgroundTasks,
    _session: dict = Depends(require_session),
    files: list[UploadFile] = File(...)
):
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if not get_teacher_by_id(teacher_id):
        raise HTTPException(status_code=404, detail="Teacher not found.")

    save_dir = FACES_DIR / str(teacher_id)
    save_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for idx, f in enumerate(files, start=1):
        if f.content_type not in ("image/jpeg", "image/png"):
            continue

        ext = ".jpg" if f.content_type == "image/jpeg" else ".png"
        filename = f"img_{idx}{ext}"
        out_path = save_dir / filename

        with open(out_path, "wb") as out_file:
            shutil.copyfileobj(f.file, out_file)
        saved += 1

    if saved == 0:
        raise HTTPException(status_code=400, detail="No valid images. Upload JPG/PNG only.")

    training_started = schedule_training(background_tasks)

    return {
        "teacher_id": teacher_id,
        "saved": saved,
        "folder": str(save_dir),
        "training_started": training_started,
        "training_message": "Training started" if training_started else "Training already running",
    }


# Enroll (Create teacher + upload faces) with auto-train
@router.post("/enroll")
async def enroll_teacher_with_faces(
    background_tasks: BackgroundTasks,
    _session: dict = Depends(require_session),
    full_name: str = Form(...),
    department: str = Form(...),
    employee_id: str = Form(...),
    files: list[UploadFile] = File(...)
):
    full_name = full_name.strip()
    department = department.strip()
    employee_id = employee_id.strip()

    if not full_name or not department or not employee_id:
        raise HTTPException(status_code=400, detail="All fields are required.")

    # REQUIRE at least 1 image
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least 1 face image is required.")

    # Only accept JPG/PNG
    valid_files = [f for f in files if f.content_type in ("image/jpeg", "image/png")]
    if len(valid_files) == 0:
        raise HTTPException(status_code=400, detail="Upload JPG/PNG only.")

    # Insert teacher ONLY IF images exist
    try:
        new_id = add_teacher(full_name, department, employee_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Employee ID already exists.")

    # Save faces to assets/faces/<id>/
    save_dir = FACES_DIR / str(new_id)
    save_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for idx, f in enumerate(valid_files, start=1):
        ext = ".jpg" if f.content_type == "image/jpeg" else ".png"
        filename = f"img_{idx}{ext}"
        out_path = save_dir / filename
        with open(out_path, "wb") as out_file:
            shutil.copyfileobj(f.file, out_file)
        saved += 1

    training_started = schedule_training(background_tasks)

    return {
        "id": new_id,
        "full_name": full_name,
        "department": department,
        "employee_id": employee_id,
        "saved": saved,
        "training_started": training_started,
        "training_message": "Training started" if training_started else "Training already running",
    }


@router.get("/teachers/{teacher_id}/dtr")
def teacher_dtr(teacher_id: int, month: str):
    # month format: YYYY-MM
    row = get_teacher_by_id(teacher_id)
    if not row:
        raise HTTPException(status_code=404, detail="Teacher not found")

    data = get_teacher_dtr_month(teacher_id, month)
    return {
        "teacher": {
            "id": row[0],
            "full_name": row[1],
            "department": row[2],
            "employee_id": row[3],
        },
        "month": month,
        "rows": [
            {
                "date": d,
                "am_in": am_in,
                "am_out": am_out,
                "pm_in": pm_in,
                "pm_out": pm_out,
            }
            for (d, am_in, am_out, pm_in, pm_out) in data
        ],
    }


