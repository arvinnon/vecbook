from fastapi import APIRouter

from backend.config import DB_PATH

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/debug/dbpath")
def dbpath():
    return {"db_path": str(DB_PATH)}
