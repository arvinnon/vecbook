import pytest
from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main
import backend.routers.core as core
import database.db as db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "vecbook_test.db"

    # Point DB to a temp file for isolation.
    monkeypatch.setattr(config, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(main, "DB_PATH", test_db, raising=False)

    db.create_tables()

    with TestClient(main.app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    res = client.post(
        "/auth/session",
        json={
            "device_id": "pytest-client",
            "device_secret": config.DEVICE_SECRET,
        },
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_debug_dbpath_disabled_by_default(client, auth_headers):
    res = client.get("/debug/dbpath", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Not found."


def test_debug_dbpath_requires_session_when_enabled(client, monkeypatch, auth_headers):
    monkeypatch.setattr(core, "ENABLE_DEBUG_ENDPOINTS", True)

    res = client.get("/debug/dbpath")
    assert res.status_code == 401

    res = client.get("/debug/dbpath", headers=auth_headers)
    assert res.status_code == 200
    assert "db_path" in res.json()


def test_session_rejects_invalid_secret(client):
    res = client.post(
        "/auth/session",
        json={"device_id": "pytest-client", "device_secret": "wrong-secret"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid device secret."


def test_create_and_list_teachers(client, auth_headers):
    payload = {
        "full_name": "Test Teacher",
        "department": "Math",
        "employee_id": "EMP_TEST_001",
    }

    res = client.post("/teachers", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] >= 1
    assert data["full_name"] == payload["full_name"]
    assert data["department"] == payload["department"]
    assert data["employee_id"] == payload["employee_id"]

    res = client.get("/teachers")
    assert res.status_code == 200
    rows = res.json()
    assert any(r["id"] == data["id"] for r in rows)


def test_teacher_dtr_empty_month(client, auth_headers):
    payload = {
        "full_name": "DTR Teacher",
        "department": "Science",
        "employee_id": "EMP_TEST_002",
    }
    res = client.post("/teachers", json=payload, headers=auth_headers)
    assert res.status_code == 200
    teacher_id = res.json()["id"]

    month = "2026-02"
    res = client.get(f"/teachers/{teacher_id}/dtr", params={"month": month})
    assert res.status_code == 200
    body = res.json()
    assert body["teacher"]["id"] == teacher_id
    assert body["month"] == month
    assert body["rows"] == []


def test_recognize_requires_session_token(client, auth_headers):
    files = {"file": ("frame.jpg", b"not-an-image", "image/jpeg")}

    res = client.post("/attendance/recognize", files=files)
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing bearer token."

    res = client.post("/attendance/recognize", files=files, headers=auth_headers)
    assert res.status_code == 400
