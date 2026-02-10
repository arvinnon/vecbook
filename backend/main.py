from fastapi import ( 
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Form,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel 

import os
import shutil
import sqlite3
import threading
from datetime import datetime

import numpy as np
import cv2 

from database.db import (
    DB_PATH,
    add_teacher,
    clear_all_tables,
    clear_attendance,
    create_tables,
    get_all_teachers,
    get_attendance_records,
    get_daily_summary,
    get_teacher_by_id,
    get_teacher_dtr_month,
    log_dtr_punch,
)

from backend.recognizer import recognize_from_frame
from backend.recognizer import reload_model
from face_recognition.trainer import train_model


app = FastAPI(title="Vecbook API")

# -----------------------------
# Training Status (in-memory)
# -----------------------------
TRAINING_LOCK = threading.Lock()
STATUS_LOCK = threading.Lock()

TRAINING_STATUS = {
    "state": "idle",          # idle | running | success | failed
    "started_at": None,       # ISO string
    "finished_at": None,      # ISO string
    "message": "",
    "last_success": None      # ISO string
}

def schedule_training(background_tasks: BackgroundTasks) -> bool:
    """
    Returns True if a training task was scheduled, False if one is already running.
    """
    if TRAINING_LOCK.locked():
        return False
    background_tasks.add_task(run_training_job)
    return True

def run_training_job():
    """Runs train_model() and updates TRAINING_STATUS."""
    if not TRAINING_LOCK.acquire(blocking=False):
        return
    try:
        with STATUS_LOCK:
            TRAINING_STATUS["state"] = "running"
            TRAINING_STATUS["started_at"] = datetime.now().isoformat(timespec="seconds")
            TRAINING_STATUS["finished_at"] = None
            TRAINING_STATUS["message"] = "Training started..."

        ok = train_model()
        reload_model()
        finished_at = datetime.now().isoformat(timespec="seconds")
        with STATUS_LOCK:
            TRAINING_STATUS["state"] = "success" if ok else "failed"
            TRAINING_STATUS["finished_at"] = finished_at
            TRAINING_STATUS["message"] = "Training completed" if ok else "Training failed: no valid faces"
            if ok:
                TRAINING_STATUS["last_success"] = finished_at

    except Exception as e:
        finished_at = datetime.now().isoformat(timespec="seconds")
        with STATUS_LOCK:
            TRAINING_STATUS["state"] = "failed"
            TRAINING_STATUS["finished_at"] = finished_at
            TRAINING_STATUS["message"] = f"Training failed: {e}"
    finally:
        TRAINING_LOCK.release()


# -----------------------------
# Models
# -----------------------------
class TeacherCreate(BaseModel):
    full_name: str
    department: str
    employee_id: str


# -----------------------------
# CORS (React dev server)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
     allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Startup
# -----------------------------
@app.on_event("startup")
def _startup():
    create_tables()


# -----------------------------
# Basic Health
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/dbpath")
def dbpath():
    return {"db_path": DB_PATH}


# -----------------------------
# Teachers
# -----------------------------
@app.get("/teachers")
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


@app.get("/teachers/{teacher_id}")
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


@app.post("/teachers")
def create_teacher(payload: TeacherCreate):
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
@app.post("/teachers/{teacher_id}/faces")
async def upload_faces(
    teacher_id: int,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...)
):
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if not get_teacher_by_id(teacher_id):
        raise HTTPException(status_code=404, detail="Teacher not found.")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # vecbook/
    save_dir = os.path.join(base_dir, "assets", "faces", str(teacher_id))
    os.makedirs(save_dir, exist_ok=True)

    saved = 0
    for idx, f in enumerate(files, start=1):
        if f.content_type not in ("image/jpeg", "image/png"):
            continue

        ext = ".jpg" if f.content_type == "image/jpeg" else ".png"
        filename = f"img_{idx}{ext}"
        out_path = os.path.join(save_dir, filename)

        with open(out_path, "wb") as out_file:
            shutil.copyfileobj(f.file, out_file)
        saved += 1

    if saved == 0:
        raise HTTPException(status_code=400, detail="No valid images. Upload JPG/PNG only.")

    # ✅ Auto-retrain in background + updates status (single-flight)
    training_started = schedule_training(background_tasks)

    return {
        "teacher_id": teacher_id,
        "saved": saved,
        "folder": save_dir,
        "training_started": training_started,
        "training_message": "Training started" if training_started else "Training already running",
    }


# -----------------------------
# Attendance + Summary
# -----------------------------
@app.get("/attendance")
def attendance(date: str | None = None):
    rows = get_attendance_records(date)
    return [
        {
            "full_name": r[0],
            "department": r[1],
            "date": r[2],
            "time_in": r[3],
            "status": r[4],
        }
        for r in rows
    ]


@app.get("/attendance/summary")
def summary(date: str):
    return get_daily_summary(date)


@app.post("/attendance/recognize")
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

    # ✅ Prevent ghost IDs (model predicts an ID not in DB)
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


# -----------------------------
# Enroll (Create teacher + upload faces) with auto-train
# -----------------------------
@app.post("/enroll")
async def enroll_teacher_with_faces(
    background_tasks: BackgroundTasks,
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

    # ✅ REQUIRE at least 1 image
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least 1 face image is required.")

    # Only accept JPG/PNG
    valid_files = [f for f in files if f.content_type in ("image/jpeg", "image/png")]
    if len(valid_files) == 0:
        raise HTTPException(status_code=400, detail="Upload JPG/PNG only.")

    # ✅ Insert teacher ONLY IF images exist
    try:
        new_id = add_teacher(full_name, department, employee_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Employee ID already exists.")

    # Save faces to assets/faces/<id>/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # vecbook/
    save_dir = os.path.join(base_dir, "assets", "faces", str(new_id))
    os.makedirs(save_dir, exist_ok=True)

    saved = 0
    for idx, f in enumerate(valid_files, start=1):
        ext = ".jpg" if f.content_type == "image/jpeg" else ".png"
        filename = f"img_{idx}{ext}"
        out_path = os.path.join(save_dir, filename)
        with open(out_path, "wb") as out_file:
            shutil.copyfileobj(f.file, out_file)
        saved += 1

    # ✅ Auto-retrain in background + updates status (single-flight)
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


# -----------------------------
# Training Status Endpoints
# -----------------------------
@app.get("/train/status")
def train_status():
    with STATUS_LOCK:
        return TRAINING_STATUS


@app.post("/train/run")
def train_run(background_tasks: BackgroundTasks):
    started = schedule_training(background_tasks)
    return {"ok": started, "message": "Training started" if started else "Training already running"}

@app.post("/admin/reset/attendance")
def reset_attendance():
    ok = clear_attendance()
    if not ok:
        raise HTTPException(status_code=400, detail="Attendance table not found. Check DB schema.")
    return {"ok": True, "message": "Attendance logs cleared"}


@app.post("/admin/reset/hard")
def reset_hard():
    # 1) clear DB
    clear_all_tables()

    # 2) delete face images
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # vecbook/
    faces_dir = os.path.join(base_dir, "assets", "faces")
    if os.path.exists(faces_dir):
        shutil.rmtree(faces_dir)
    os.makedirs(faces_dir, exist_ok=True)

    # 3) delete model
    model_path = os.path.join(base_dir, "face_recognition", "face_model.yml")
    if os.path.exists(model_path):
        os.remove(model_path)

    # 4) reset training status (optional)
    with STATUS_LOCK:
        TRAINING_STATUS.update({
            "state": "idle",
            "started_at": None,
            "finished_at": None,
            "message": "System reset (teachers + faces cleared).",
            "last_success": None
        })

    return {"ok": True, "message": "✅ Reset complete: teachers + faces + model cleared"}

@app.get("/teachers/{teacher_id}/dtr")
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
