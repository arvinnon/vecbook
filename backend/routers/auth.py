import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.security import issue_session_token, require_session, verify_device_secret

router = APIRouter()


class SessionCreate(BaseModel):
    device_id: str
    device_secret: str


@router.post("/auth/session")
def create_session(payload: SessionCreate):
    device_id = payload.device_id.strip()
    device_secret = payload.device_secret.strip()

    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required.")
    if not device_secret:
        raise HTTPException(status_code=400, detail="Device secret is required.")
    if not verify_device_secret(device_secret):
        raise HTTPException(status_code=401, detail="Invalid device secret.")

    token, claims = issue_session_token(device_id)
    now = int(time.time())
    return {
        "access_token": token,
        "token_type": "bearer",
        "device_id": claims["sub"],
        "expires_at": claims["exp"],
        "expires_in": max(0, int(claims["exp"]) - now),
    }


@router.get("/auth/me")
def auth_me(session: dict = Depends(require_session)):
    return {
        "device_id": session.get("sub"),
        "expires_at": session.get("exp"),
        "issued_at": session.get("iat"),
    }
