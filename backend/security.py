import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Header, HTTPException

from backend.config import AUTH_TOKEN_TTL_SECONDS, SIGNING_KEY


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload_b64: str) -> str:
    digest = hmac.new(
        SIGNING_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def issue_session_token(subject: str, role: str = "admin") -> tuple[str, dict[str, Any]]:
    clean_subject = (subject or "").strip()
    clean_role = (role or "").strip() or "admin"
    now = int(time.time())
    exp = now + AUTH_TOKEN_TTL_SECONDS
    payload = {
        "sub": clean_subject,
        "role": clean_role,
        "iat": now,
        "exp": exp,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    token = f"{payload_b64}.{_sign(payload_b64)}"
    return token, payload


def decode_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None

    payload_b64, signature = token.split(".", 1)
    expected = _sign(payload_b64)
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload_raw = _b64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_raw)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    sub = payload.get("sub")
    role = payload.get("role", "admin")
    exp = payload.get("exp")
    if not isinstance(sub, str) or not sub.strip():
        return None
    if not isinstance(role, str) or not role.strip():
        return None
    if not isinstance(exp, int):
        return None
    if exp < int(time.time()):
        return None

    payload["role"] = role
    return payload


def require_session(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme.")

    payload = decode_session_token(token.strip())
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    return payload
