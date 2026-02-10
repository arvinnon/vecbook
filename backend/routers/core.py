from fastapi import APIRouter

from backend.config import DB_PATH, MATCH_CONFIRMATIONS, MATCH_THRESHOLD, SESSION_TTL_SECONDS

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/debug/dbpath")
def dbpath():
    return {"db_path": str(DB_PATH)}


@router.get("/config/recognition")
def recognition_config():
    return {
        "match_threshold": MATCH_THRESHOLD,
        "match_confirmations": MATCH_CONFIRMATIONS,
        "session_ttl_seconds": SESSION_TTL_SECONDS,
    }
