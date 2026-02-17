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
        "/auth/login",
        json={
            "username": config.ADMIN_USERNAME,
            "password": config.ADMIN_PASSWORD,
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


def test_login_rejects_invalid_credentials(client):
    res = client.post(
        "/auth/login",
        json={"username": config.ADMIN_USERNAME, "password": "wrong-password"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid admin credentials."


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

    res = client.get("/teachers", headers=auth_headers)
    assert res.status_code == 200
    rows = res.json()
    assert any(r["id"] == data["id"] for r in rows)


def test_enroll_without_faces_is_rejected(client, auth_headers):
    payload = {
        "full_name": "No Face Teacher",
        "department": "English",
        "employee_id": "EMP_TEST_NOFACE_001",
    }

    res = client.post("/enroll", data=payload, headers=auth_headers)
    assert res.status_code == 400
    assert "Please capture at least 8 face images before enrolling." in res.json()["detail"]

    list_res = client.get("/teachers", headers=auth_headers)
    assert list_res.status_code == 200
    rows = list_res.json()
    assert all(r["employee_id"] != payload["employee_id"] for r in rows)


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
    res = client.get(f"/teachers/{teacher_id}/dtr", params={"month": month}, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["teacher"]["id"] == teacher_id
    assert body["month"] == month
    assert body["rows"] == []


def test_summary_includes_non_punch_records(client, auth_headers):
    conn = db.connect_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO teachers (full_name, department, employee_id)
        VALUES (?, ?, ?)
        """,
        ("Summary Teacher", "Science", "EMP_SUMMARY_001"),
    )
    teacher_id = cur.lastrowid

    cur.execute(
        """
        INSERT INTO attendance_daily (teacher_id, date, status, remarks, scan_attempts, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            teacher_id,
            "2026-02-10",
            "Outside Hours",
            "Scan is during lunch break.",
            1,
            "LiveFaceCapture",
        ),
    )
    conn.commit()
    conn.close()

    records_res = client.get("/attendance", params={"date": "2026-02-10"}, headers=auth_headers)
    assert records_res.status_code == 200
    records = records_res.json()
    assert len(records) == 1
    assert records[0]["status"] == "Lunch break"

    summary_res = client.get("/attendance/summary", params={"date": "2026-02-10"}, headers=auth_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total"] == 1
    assert summary["on_time"] == 0
    assert summary["late"] == 0


def test_admin_scan_events_with_filters(client, auth_headers):
    conn = db.connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO teachers (full_name, department, employee_id)
        VALUES (?, ?, ?)
        """,
        ("Audit Teacher", "History", "EMP_AUDIT_001"),
    )
    teacher_id = cur.lastrowid
    conn.commit()
    conn.close()

    db.process_attendance_scan_v2(
        teacher_id=teacher_id,
        full_name="Audit Teacher",
        department="History",
        confidence=20.0,
        scan_verified=True,
        reason=None,
        event_date="2026-02-10",
        event_time="08:10:00",
    )

    res = client.get("/admin/scan-events", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(int(r["teacher_id"]) == teacher_id for r in body["rows"] if r["teacher_id"] is not None)

    filtered = client.get(
        "/admin/scan-events",
        params={"teacher_id": teacher_id, "requires_review": False},
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert all((r["teacher_id"] == teacher_id) for r in filtered_body["rows"])


def test_read_endpoints_require_session(client, auth_headers):
    res = client.get("/teachers")
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing bearer token."

    res = client.get("/attendance")
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing bearer token."

    res = client.get("/attendance/summary", params={"date": "2026-02-10"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing bearer token."

    res = client.get("/teachers", headers=auth_headers)
    assert res.status_code == 200

    res = client.get("/attendance", headers=auth_headers)
    assert res.status_code == 200


def test_recognize_requires_session_token(client, auth_headers):
    files = {"file": ("frame.jpg", b"not-an-image", "image/jpeg")}

    res = client.post("/attendance/recognize", files=files)
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing bearer token."

    res = client.post("/attendance/recognize", files=files, headers=auth_headers)
    assert res.status_code == 400
