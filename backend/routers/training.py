from fastapi import APIRouter, BackgroundTasks, Depends

from backend.security import require_api_key
from backend.services.training import get_training_status, schedule_training

router = APIRouter()


@router.get("/train/status")
def train_status():
    return get_training_status()


@router.post("/train/run")
def train_run(background_tasks: BackgroundTasks, _auth: None = Depends(require_api_key)):
    started = schedule_training(background_tasks)
    return {"ok": started, "message": "Training started" if started else "Training already running"}
