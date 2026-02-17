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
RERUN_LOCK = threading.Lock()
TRAINING_RERUN_REQUESTED = False

TRAINING_STATUS = {
    "state": "idle",          # idle | running | success | failed
    "started_at": None,       # ISO string
    "finished_at": None,      # ISO string
    "message": "",
    "last_success": None,     # ISO string
    "queued": False,          # whether another run is queued
}


def schedule_training(background_tasks: BackgroundTasks) -> str:
    """
    Returns:
      - "started": training job scheduled now
      - "queued":  another pass queued after current run
      - "already_running": already running and queue already set
    """
    global TRAINING_RERUN_REQUESTED

    if TRAINING_LOCK.locked():
        with RERUN_LOCK:
            if TRAINING_RERUN_REQUESTED:
                return "already_running"
            TRAINING_RERUN_REQUESTED = True
        with STATUS_LOCK:
            TRAINING_STATUS["queued"] = True
            TRAINING_STATUS["message"] = "Training in progress; next pass queued."
        return "queued"
    background_tasks.add_task(run_training_job)
    with STATUS_LOCK:
        TRAINING_STATUS["queued"] = False
    return "started"


def run_training_job() -> None:
    """Runs train_model() and updates TRAINING_STATUS."""
    global TRAINING_RERUN_REQUESTED

    if not TRAINING_LOCK.acquire(blocking=False):
        return
    try:
        while True:
            with STATUS_LOCK:
                TRAINING_STATUS["state"] = "running"
                TRAINING_STATUS["started_at"] = datetime.now().isoformat(timespec="seconds")
                TRAINING_STATUS["finished_at"] = None
                TRAINING_STATUS["message"] = "Training started..."
                TRAINING_STATUS["queued"] = False

            ok = train_model()
            reload_model()
            finished_at = datetime.now().isoformat(timespec="seconds")

            rerun_queued = False
            with RERUN_LOCK:
                rerun_queued = TRAINING_RERUN_REQUESTED
                TRAINING_RERUN_REQUESTED = False

            with STATUS_LOCK:
                TRAINING_STATUS["state"] = "success" if ok else "failed"
                TRAINING_STATUS["finished_at"] = finished_at
                if rerun_queued:
                    TRAINING_STATUS["message"] = "Training completed; queued retrain starting..."
                    TRAINING_STATUS["queued"] = True
                else:
                    TRAINING_STATUS["message"] = "Training completed" if ok else "Training failed: no valid faces"
                    TRAINING_STATUS["queued"] = False
                if ok:
                    TRAINING_STATUS["last_success"] = finished_at

            if not rerun_queued:
                break

    except Exception as e:
        finished_at = datetime.now().isoformat(timespec="seconds")
        with STATUS_LOCK:
            TRAINING_STATUS["state"] = "failed"
            TRAINING_STATUS["finished_at"] = finished_at
            TRAINING_STATUS["message"] = f"Training failed: {e}"
            TRAINING_STATUS["queued"] = False
    finally:
        TRAINING_LOCK.release()


def get_training_status() -> dict:
    with STATUS_LOCK:
        return dict(TRAINING_STATUS)


def reset_training_status(message: str = "System reset (teachers + faces cleared).") -> None:
    global TRAINING_RERUN_REQUESTED
    with RERUN_LOCK:
        TRAINING_RERUN_REQUESTED = False
    with STATUS_LOCK:
        TRAINING_STATUS.update({
            "state": "idle",
            "started_at": None,
            "finished_at": None,
            "message": message,
            "last_success": None,
            "queued": False,
        })
