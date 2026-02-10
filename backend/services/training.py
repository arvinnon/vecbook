import threading
from datetime import datetime

from fastapi import BackgroundTasks

from backend.recognizer import reload_model
from face_recognition.trainer import train_model

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


def run_training_job() -> None:
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


def get_training_status() -> dict:
    with STATUS_LOCK:
        return dict(TRAINING_STATUS)


def reset_training_status(message: str = "System reset (teachers + faces cleared).") -> None:
    with STATUS_LOCK:
        TRAINING_STATUS.update({
            "state": "idle",
            "started_at": None,
            "finished_at": None,
            "message": message,
            "last_success": None
        })
