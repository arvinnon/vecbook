from fastapi import APIRouter, BackgroundTasks, Depends

from backend.security import require_session
from backend.services.training import get_training_status, schedule_training

router = APIRouter()


@router.get("/train/status")
def train_status():
    return get_training_status()


@router.post("/train/run")
def train_run(background_tasks: BackgroundTasks, _session: dict = Depends(require_session)):
    state = schedule_training(background_tasks)
    if state == "started":
        return {"ok": True, "queued": False, "message": "Training started"}
    if state == "queued":
        return {"ok": True, "queued": True, "message": "Training in progress; next pass queued"}
    return {"ok": False, "queued": True, "message": "Training already running"}


