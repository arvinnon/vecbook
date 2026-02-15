import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Header, HTTPException

from backend.config import AUTH_TOKEN_TTL_SECONDS, DEVICE_SECRET, SIGNING_KEY


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


def verify_device_secret(device_secret: str) -> bool:
    expected = DEVICE_SECRET.strip()
    candidate = (device_secret or "").strip()
    if not expected:
        return False
    return hmac.compare_digest(candidate, expected)


def issue_session_token(device_id: str) -> tuple[str, dict[str, Any]]:
    now = int(time.time())
    exp = now + AUTH_TOKEN_TTL_SECONDS
    payload = {
        "sub": device_id.strip(),
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
    exp = payload.get("exp")
    if not isinstance(sub, str) or not sub.strip():
        return None
    if not isinstance(exp, int):
        return None
    if exp < int(time.time()):
        return None

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
