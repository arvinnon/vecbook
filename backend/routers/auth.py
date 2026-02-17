import time
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.security import issue_session_token, require_session
from database.db import create_tables, verify_admin_credentials

router = APIRouter()


class AdminLogin(BaseModel):
    username: str
    password: str


def _issue_admin_token(payload: AdminLogin) -> dict:
    username = payload.username.strip()
    password = payload.password.strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    try:
        admin = verify_admin_credentials(username, password)
    except sqlite3.OperationalError:
        # Self-heal when DB schema is missing (e.g., startup/lifespan skipped).
        try:
            create_tables()
            admin = verify_admin_credentials(username, password)
        except sqlite3.OperationalError:
            raise HTTPException(
                status_code=503,
                detail="Authentication service unavailable. Please retry.",
            )

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    token, claims = issue_session_token(admin["username"], role="admin")
    now = int(time.time())
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": claims["sub"],
        "role": claims["role"],
        "expires_at": claims["exp"],
        "expires_in": max(0, int(claims["exp"]) - now),
    }


@router.post("/auth/login")
def admin_login(payload: AdminLogin):
    return _issue_admin_token(payload)


@router.post("/auth/session")
def create_session_alias(payload: AdminLogin):
    # Backward-compatible alias for older clients.
    return _issue_admin_token(payload)


@router.get("/auth/me")
def auth_me(session: dict = Depends(require_session)):
    return {
        "username": session.get("sub"),
        "role": session.get("role", "admin"),
        "expires_at": session.get("exp"),
        "issued_at": session.get("iat"),
    }
