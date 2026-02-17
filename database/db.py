import hashlib
import hmac
import json
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Any, Literal, TypedDict, cast

from backend.config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    AM_END,
    AM_START,
    ATTENDANCE_ABSENCE_CUTOFF,
    ATTENDANCE_AUTO_CLOSE_CUTOFF,
    ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS,
    ATTENDANCE_GRACE_MINUTES,
    DB_PATH,
    PM_END,
    PM_START,
)


PASSWORD_HASH_ALGO = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 120_000
ATTENDANCE_V2_MIGRATION_FILE = Path(__file__).resolve().parent / "migrations" / "001_attendance_v2.sql"


def _hash_password(password: str, *, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_ALGO}${PASSWORD_HASH_ITERATIONS}${salt_value}${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, rounds_text, salt_value, expected_digest = password_hash.split("$", 3)
        rounds = int(rounds_text)
    except (ValueError, TypeError):
        return False

    if algo != PASSWORD_HASH_ALGO or rounds <= 0:
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("utf-8"),
        rounds,
    ).hex()
    return hmac.compare_digest(candidate_digest, expected_digest)


def connect_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    # recommended with FK tables
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _ensure_default_admin(cursor: sqlite3.Cursor) -> None:
    username = (ADMIN_USERNAME or "").strip()
    password = (ADMIN_PASSWORD or "").strip()
    if not username or not password:
        return

    cursor.execute(
        """
        SELECT id
        FROM admin_users
        WHERE username = ? COLLATE NOCASE
        """,
        (username,),
    )
    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO admin_users (username, password_hash)
        VALUES (?, ?)
        """,
        (username, _hash_password(password)),
    )


def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        department TEXT,
        employee_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # ✅ DTR table (per teacher per date)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dtr_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        date TEXT NOT NULL,              -- YYYY-MM-DD
        am_in TEXT,                      -- HH:MM:SS
        am_out TEXT,                     -- HH:MM:SS
        pm_in TEXT,                      -- HH:MM:SS
        pm_out TEXT,                     -- HH:MM:SS
        event_time TEXT,                 -- HH:MM:SS (out-of-shift/lunch scans)
        status TEXT,                     -- status override
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        UNIQUE(teacher_id, date)
    )
    """)

    # Drop legacy unused table if present.
    cursor.execute("DROP TABLE IF EXISTS face_embeddings;")

    # Migration for older DB
    try:
        cursor.execute("ALTER TABLE dtr_logs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE dtr_logs ADD COLUMN event_time TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE dtr_logs ADD COLUMN status TEXT;")
    except sqlite3.OperationalError:
        pass

    _ensure_default_admin(cursor)

    # Commit base schema first so v2 migration can safely manage its own
    # transaction block.
    conn.commit()
    ensure_attendance_v2_schema(conn)

    conn.commit()
    conn.close()


# -----------------------------
# Teachers
# -----------------------------
def get_all_teachers():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, full_name, department, employee_id, created_at
        FROM teachers
        ORDER BY full_name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def add_teacher(full_name: str, department: str, employee_id: str) -> int:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO teachers (full_name, department, employee_id)
        VALUES (?, ?, ?)
    """, (full_name, department, employee_id))
    teacher_id = cur.lastrowid
    conn.commit()
    conn.close()
    return teacher_id


def get_teacher_by_id(teacher_id: int):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, full_name, department, employee_id
        FROM teachers
        WHERE id = ?
    """, (teacher_id,))
    row = cur.fetchone()
    conn.close()
    return row


# -----------------------------
# Admin users
# -----------------------------
def create_admin_user(username: str, password: str) -> int:
    clean_username = username.strip()
    clean_password = password.strip()
    if not clean_username or not clean_password:
        raise ValueError("Username and password are required.")

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO admin_users (username, password_hash)
        VALUES (?, ?)
        """,
        (clean_username, _hash_password(clean_password)),
    )
    admin_id = cur.lastrowid
    conn.commit()
    conn.close()
    return admin_id


def verify_admin_credentials(username: str, password: str) -> dict | None:
    clean_username = username.strip()
    clean_password = password.strip()
    if not clean_username or not clean_password:
        return None

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, password_hash
        FROM admin_users
        WHERE username = ? COLLATE NOCASE
        """,
        (clean_username,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    admin_id, saved_username, password_hash = row
    if not _verify_password(clean_password, password_hash):
        return None

    return {"id": admin_id, "username": saved_username}


# -----------------------------
# DTR Punch Logic
# -----------------------------
def log_dtr_punch(teacher_id: int):
    """
    Punch logic:
      - before 12:00 => AM
          1st scan = AM IN
          2nd scan = AM OUT
      - 12:00+ => PM
          1st scan = PM IN
          2nd scan = PM OUT

    Returns:
      {
        "logged": True/False,
        "date": "YYYY-MM-DD",
        "time": "HH:MM:SS",
        "slot": "am_in|am_out|pm_in|pm_out",
        "status": "On-Time|Late|Recorded",
        "already_complete": bool
      }
    """
    conn = connect_db()
    cur = conn.cursor()

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    punch_time = now.strftime("%H:%M:%S")
    now_time = now.time()

    is_am_window = AM_START <= now_time < AM_END
    is_pm_window = PM_START <= now_time < PM_END

    if not is_am_window and not is_pm_window:
        reason = "lunch_break" if AM_END <= now_time < PM_START else "out_of_shift"
        status_label = "Lunch break" if reason == "lunch_break" else "Outside shift hours"

        cur.execute("""
            SELECT id FROM dtr_logs
            WHERE teacher_id=? AND date=?
        """, (teacher_id, date))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO dtr_logs (teacher_id, date, event_time, status)
                VALUES (?, ?, ?, ?)
            """, (teacher_id, date, punch_time, status_label))
        else:
            cur.execute("""
                UPDATE dtr_logs
                SET event_time=?,
                    status=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE teacher_id=? AND date=?
            """, (punch_time, status_label, teacher_id, date))

        conn.commit()
        conn.close()
        return {
            "logged": False,
            "reason": reason,
            "date": date,
            "time": punch_time,
            "already_complete": False,
        }

    # Ensure row exists
    cur.execute("""
        SELECT am_in, am_out, pm_in, pm_out
        FROM dtr_logs
        WHERE teacher_id=? AND date=?
    """, (teacher_id, date))
    row = cur.fetchone()

    if not row:
        cur.execute("""
            INSERT INTO dtr_logs (teacher_id, date)
            VALUES (?, ?)
        """, (teacher_id, date))
        conn.commit()
        am_in = am_out = pm_in = pm_out = None
    else:
        am_in, am_out, pm_in, pm_out = row

    slot = None
    status = "Recorded"
    already_complete = False

    if is_am_window:
        if not am_in:
            slot = "am_in"
            status = "On-Time" if now_time <= AM_START else "Late"
        elif not am_out:
            slot = "am_out"
        else:
            already_complete = True
    else:
        if not pm_in:
            slot = "pm_in"
            status = "On-Time" if now_time <= PM_START else "Late"
        elif not pm_out:
            slot = "pm_out"
        else:
            already_complete = True

    if already_complete:
        conn.close()
        return {
            "logged": False,
            "reason": "day_complete",
            "date": date,
            "time": punch_time,
            "already_complete": True,
        }

    cur.execute(f"""
        UPDATE dtr_logs
        SET {slot}=?,
            status=NULL,
            updated_at=CURRENT_TIMESTAMP
        WHERE teacher_id=? AND date=?
    """, (punch_time, teacher_id, date))

    conn.commit()
    conn.close()

    return {
        "logged": True,
        "date": date,
        "time_in": punch_time,   # keep naming consistent with your frontend
        "slot": slot,
        "status": status,
        "already_complete": False
    }


def _coerce_clock_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%H:%M:%S").time()
    except (TypeError, ValueError):
        return None


def get_teacher_dtr_month(teacher_id: int, month: str):
    """
    month = "YYYY-MM"
    returns list of rows:
      (date, am_in, am_out, pm_in, pm_out)
    """
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    run_attendance_maintenance_v2(conn=conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, time_in, time_out, status, remarks, scan_attempts
        FROM attendance_daily
        WHERE teacher_id = ?
          AND date LIKE ?
          AND (
              scan_attempts > 0
              OR time_in IS NOT NULL
              OR time_out IS NOT NULL
              OR status <> 'Absent'
              OR remarks IS NOT NULL
          )
        ORDER BY date ASC
        """,
        (teacher_id, f"{month}-%"),
    )
    rows = cur.fetchall()
    conn.close()

    out: list[tuple[str, str | None, str | None, str | None, str | None]] = []
    for dt, time_in, time_out, _, _, _ in rows:
        am_in = am_out = pm_in = pm_out = None
        in_time = _coerce_clock_time(time_in)
        out_time = _coerce_clock_time(time_out)

        if time_in:
            if in_time and in_time >= PM_START:
                pm_in = str(time_in)
            else:
                am_in = str(time_in)

        if time_out:
            if out_time and out_time < PM_START:
                am_out = str(time_out)
            else:
                pm_out = str(time_out)

        out.append((str(dt), am_in, am_out, pm_in, pm_out))
    return out


# -----------------------------
# Attendance list + summary (attendance_daily source)
# -----------------------------
def get_attendance_records(date=None):
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    run_attendance_maintenance_v2(conn=conn)
    cur = conn.cursor()

    where = [
        """
        (
            ad.scan_attempts > 0
            OR ad.time_in IS NOT NULL
            OR ad.time_out IS NOT NULL
            OR ad.status <> 'Absent'
            OR ad.remarks IS NOT NULL
        )
        """
    ]
    params: list[Any] = []

    if date:
        where.append("ad.date = ?")
        params.append(date)

    query = f"""
        SELECT
            ad.id,
            t.full_name,
            t.department,
            ad.date,
            ad.time_in,
            ad.time_out,
            ad.status,
            ad.remarks,
            (
                SELECT se.event_time
                FROM scan_events se
                WHERE se.dtr_record_id = ad.id
                ORDER BY se.id DESC
                LIMIT 1
            ) AS last_event_time
        FROM attendance_daily ad
        JOIN teachers t ON t.id = ad.teacher_id
        WHERE {" AND ".join(where)}
        ORDER BY ad.date DESC, COALESCE(ad.time_in, ad.time_out, last_event_time, '00:00:00') ASC
    """
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    out: list[tuple[int, str, str, str, str | None, str | None, str, str | None]] = []
    for log_id, full_name, department, dt, time_in, time_out, status_value, remarks, last_event_time in rows:
        status_clean = str(status_value or "").strip()
        remarks_clean = str(remarks or "").strip()
        status_display = "Recorded"

        if status_clean == "Present":
            status_display = "On-Time"
        elif status_clean == "Late":
            status_display = "Late"
        elif status_clean == "Outside Hours":
            remarks_lc = remarks_clean.lower()
            if "lunch" in remarks_lc:
                status_display = "Lunch break"
            elif "outside shift" in remarks_lc:
                status_display = "Outside shift hours"
            else:
                status_display = "Outside Hours"
        elif status_clean:
            status_display = status_clean

        time_in_display = str(time_in) if time_in else None
        time_out_display = str(time_out) if time_out else None
        last_scan_display = str(last_event_time) if last_event_time else None
        out.append(
            (
                int(log_id),
                str(full_name),
                str(department or ""),
                str(dt),
                time_in_display,
                time_out_display,
                status_display,
                last_scan_display,
            )
        )
    return out


def get_daily_summary(date):
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    run_attendance_maintenance_v2(conn=conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            COUNT(1) AS total,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS on_time,
            SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN status = 'Auto-Closed' THEN 1 ELSE 0 END) AS auto_closed
        FROM attendance_daily
        WHERE date = ?
          AND (
              scan_attempts > 0
              OR time_in IS NOT NULL
              OR time_out IS NOT NULL
              OR status <> 'Absent'
              OR remarks IS NOT NULL
          )
        """,
        (date,),
    )
    row = cur.fetchone()
    conn.close()
    total = int(row[0] or 0) if row else 0
    on_time = int(row[1] or 0) if row else 0
    late = int(row[2] or 0) if row else 0
    absent = int(row[3] or 0) if row else 0
    auto_closed = int(row[4] or 0) if row else 0
    return {
        "total": total,
        "on_time": on_time,
        "late": late,
        "absent": absent,
        "auto_closed": auto_closed,
    }


# -----------------------------
# Resets
# -----------------------------
def clear_attendance():
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    cur = conn.cursor()

    # ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_daily'")
    if not cur.fetchone():
        conn.close()
        return False

    cur.execute("DELETE FROM scan_events;")
    cur.execute("DELETE FROM attendance_daily;")
    cur.execute("DELETE FROM dtr_logs;")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='scan_events';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='attendance_daily';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='dtr_logs';")
    conn.commit()
    conn.close()
    return True


def clear_all_tables():
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM scan_events;")
    cur.execute("DELETE FROM attendance_daily;")
    cur.execute("DELETE FROM dtr_logs;")
    cur.execute("DELETE FROM teachers;")

    cur.execute("DELETE FROM sqlite_sequence WHERE name='scan_events';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='attendance_daily';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='dtr_logs';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='teachers';")

    conn.commit()
    conn.close()


def delete_attendance_record(log_id: int) -> bool:
    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT teacher_id, date
        FROM attendance_daily
        WHERE id = ?
        """,
        (log_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    teacher_id, event_date = row
    cur.execute("DELETE FROM attendance_daily WHERE id = ?", (log_id,))
    # Keep legacy mirror table consistent while the codebase still carries it.
    cur.execute(
        """
        DELETE FROM dtr_logs
        WHERE teacher_id = ? AND date = ?
        """,
        (teacher_id, event_date),
    )
    conn.commit()
    conn.close()
    return True


def delete_dtr_log(log_id: int) -> bool:
    # Backward-compatible wrapper for existing imports/routes.
    return delete_attendance_record(log_id)


# -----------------------------
# Attendance v2 Retrofit Contract
# -----------------------------
DecisionCode = Literal[
    "TIME_IN_SET",
    "TIME_OUT_SET",
    "AUTO_CLOSED_SET",
    "ABSENCE_MARKED",
    "OUTSIDE_SCHEDULE",
    "OUTSIDE_SCHEDULE_LUNCH",
    "DAY_COMPLETE",
    "FACE_PENDING_CONFIRMATION",
    "FACE_LOW_CONFIDENCE",
    "FACE_NO_MATCH",
    "UNKNOWN_FACE_NOT_ENROLLED",
    "DUPLICATE_IGNORED",
    "ERROR",
]

DtrAction = Literal["none", "time_in", "time_out"]
AttendanceStatus = Literal["Present", "Late", "Absent", "Outside Hours", "Auto-Closed"]


class AttendanceV2ScanResult(TypedDict):
    verified: bool
    logged: bool
    decision_code: DecisionCode
    message: str
    teacher_id: int | None
    full_name: str | None
    department: str | None
    confidence: float | None
    dtr_action: DtrAction
    date: str
    event_time: str
    time_in: str | None
    time_out: str | None
    status: AttendanceStatus | None
    remarks: str | None
    late_by_minutes: int | None
    worked_minutes: int | None
    undertime_minutes: int | None
    auto_closed: bool
    scan_event_id: int
    dtr_record_id: int | None
    scan_attempts_today: int
    requires_admin_review: bool
    retry_after_seconds: int | None
    request_id: str | None


def ensure_attendance_v2_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure the v2 tables/indexes exist (`attendance_daily`, `scan_events`).

    Intended usage:
    - Called during startup migration phase before v2 attendance logic is enabled.
    - SQL source: `database/migrations/001_attendance_v2.sql`.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name IN ('attendance_daily', 'scan_events')
        """
    )
    existing = {str(row[0]) for row in cur.fetchall()}
    if not {"attendance_daily", "scan_events"}.issubset(existing):
        sql = ATTENDANCE_V2_MIGRATION_FILE.read_text(encoding="utf-8")
        conn.executescript(sql)

    _ensure_attendance_v2_columns(conn)


def _ensure_attendance_v2_columns(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(attendance_daily)")
    cols = {str(row[1]) for row in cur.fetchall()}

    col_defs: list[tuple[str, str]] = [
        ("scheduled_start", "TEXT"),
        ("scheduled_end", "TEXT"),
        ("grace_minutes", "INTEGER NOT NULL DEFAULT 10"),
        ("late_by_minutes", "INTEGER NOT NULL DEFAULT 0"),
        ("worked_minutes", "INTEGER"),
        ("undertime_minutes", "INTEGER"),
        ("auto_closed_at", "TIMESTAMP"),
        ("absence_marked_at", "TIMESTAMP"),
    ]
    for col_name, col_def in col_defs:
        if col_name in cols:
            continue
        cur.execute(f"ALTER TABLE attendance_daily ADD COLUMN {col_name} {col_def}")

    cur.execute(
        """
        UPDATE attendance_daily
        SET scheduled_start = COALESCE(scheduled_start, ?),
            scheduled_end = COALESCE(scheduled_end, ?),
            grace_minutes = COALESCE(grace_minutes, ?),
            late_by_minutes = COALESCE(late_by_minutes, 0)
        WHERE scheduled_start IS NULL
           OR scheduled_end IS NULL
           OR grace_minutes IS NULL
           OR late_by_minutes IS NULL
        """,
        (
            AM_START.strftime("%H:%M:%S"),
            PM_END.strftime("%H:%M:%S"),
            ATTENDANCE_GRACE_MINUTES,
        ),
    )


def get_or_create_attendance_daily_v2(
    teacher_id: int,
    date: str,
    *,
    source: str = "LiveFaceCapture",
    scheduled_start: str | None = None,
    scheduled_end: str | None = None,
    grace_minutes: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """
    Return existing `attendance_daily.id` for (teacher_id, date) or create it.
    """
    owns_conn = conn is None
    active_conn = conn or connect_db()
    ensure_attendance_v2_schema(active_conn)
    cur = active_conn.cursor()
    default_start = scheduled_start or AM_START.strftime("%H:%M:%S")
    default_end = scheduled_end or PM_END.strftime("%H:%M:%S")
    default_grace = ATTENDANCE_GRACE_MINUTES if grace_minutes is None else max(0, int(grace_minutes))

    try:
        cur.execute(
            """
            SELECT id, scheduled_start, scheduled_end, grace_minutes
            FROM attendance_daily
            WHERE teacher_id = ? AND date = ?
            """,
            (teacher_id, date),
        )
        row = cur.fetchone()
        if row:
            row_id = int(row[0])
            row_start = str(row[1]) if row[1] else None
            row_end = str(row[2]) if row[2] else None
            row_grace = int(row[3]) if row[3] is not None else None
            if row_start != default_start or row_end != default_end or row_grace != default_grace:
                cur.execute(
                    """
                    UPDATE attendance_daily
                    SET scheduled_start = COALESCE(scheduled_start, ?),
                        scheduled_end = COALESCE(scheduled_end, ?),
                        grace_minutes = COALESCE(grace_minutes, ?)
                    WHERE id = ?
                    """,
                    (default_start, default_end, default_grace, row_id),
                )
            return row_id

        cur.execute(
            """
            INSERT INTO attendance_daily (
                teacher_id,
                date,
                source,
                scheduled_start,
                scheduled_end,
                grace_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (teacher_id, date, source, default_start, default_end, default_grace),
        )
        if owns_conn:
            active_conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        cur.execute(
            """
            SELECT id
            FROM attendance_daily
            WHERE teacher_id = ? AND date = ?
            """,
            (teacher_id, date),
        )
        row = cur.fetchone()
        if not row:
            raise
        return int(row[0])
    finally:
        if owns_conn:
            active_conn.close()


def insert_scan_event_v2(
    *,
    decision_code: DecisionCode,
    message: str,
    event_date: str,
    event_time: str,
    teacher_id: int | None = None,
    recognized_label: int | None = None,
    confidence: float | None = None,
    source: str = "LiveFaceCapture",
    session_id: str | None = None,
    request_id: str | None = None,
    requires_review: bool = False,
    error_code: str | None = None,
    dtr_record_id: int | None = None,
    payload_json: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """
    Insert a single append-only scan audit event and return `scan_events.id`.
    """
    owns_conn = conn is None
    active_conn = conn or connect_db()
    ensure_attendance_v2_schema(active_conn)
    cur = active_conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO scan_events (
                teacher_id,
                recognized_label,
                confidence,
                decision_code,
                message,
                event_date,
                event_time,
                source,
                session_id,
                request_id,
                requires_review,
                error_code,
                dtr_record_id,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                teacher_id,
                recognized_label,
                confidence,
                decision_code,
                message,
                event_date,
                event_time,
                source,
                session_id,
                request_id,
                1 if requires_review else 0,
                error_code,
                dtr_record_id,
                payload_json,
            ),
        )
        event_id = int(cur.lastrowid)
        if owns_conn:
            active_conn.commit()
        return event_id
    except sqlite3.IntegrityError:
        if request_id:
            cur.execute(
                """
                SELECT id
                FROM scan_events
                WHERE request_id = ?
                LIMIT 1
                """,
                (request_id,),
            )
            row = cur.fetchone()
            if row:
                return int(row[0])
        raise
    finally:
        if owns_conn:
            active_conn.close()


def _normalize_event_datetime(event_date: str, event_time: str) -> tuple[str, str, time]:
    try:
        stamp = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        stamp = datetime.now()
    return stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M:%S"), stamp.time()


def _in_am_window(scan_time: time) -> bool:
    return AM_START <= scan_time < AM_END


def _in_pm_window(scan_time: time) -> bool:
    return PM_START <= scan_time < PM_END


def _is_lunch_break(scan_time: time) -> bool:
    return AM_END <= scan_time < PM_START


def _hms(value: time) -> str:
    return value.strftime("%H:%M:%S")


def _add_minutes_to_time(base: time, minutes: int) -> time:
    anchor = datetime.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    base_dt = datetime.combine(anchor.date(), base)
    return (base_dt + timedelta(minutes=max(0, int(minutes)))).time()


def _minutes_between_clock_times(start_time: str | None, end_time: str | None) -> int | None:
    if not start_time or not end_time:
        return None
    try:
        start_dt = datetime.strptime(f"2000-01-01 {start_time}", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"2000-01-01 {end_time}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    delta_minutes = int((end_dt - start_dt).total_seconds() // 60)
    return max(0, delta_minutes)


def _shift_start_for_scan(scan_time: time) -> time:
    if _in_pm_window(scan_time):
        return PM_START
    return AM_START


def _time_in_status(scan_time: time, *, scheduled_start: time, grace_minutes: int) -> tuple[AttendanceStatus, int]:
    grace_deadline = _add_minutes_to_time(scheduled_start, grace_minutes)
    if scan_time <= grace_deadline:
        return "Present", 0
    late_minutes = _minutes_between_clock_times(_hms(scheduled_start), _hms(scan_time))
    return "Late", int(late_minutes or 0)


def _scheduled_minutes(scheduled_start: str | None, scheduled_end: str | None) -> int | None:
    return _minutes_between_clock_times(scheduled_start, scheduled_end)


def _compute_work_and_undertime(
    *,
    time_in: str | None,
    time_out: str | None,
    scheduled_start: str | None,
    scheduled_end: str | None,
) -> tuple[int | None, int | None]:
    worked = _minutes_between_clock_times(time_in, time_out)
    sched = _scheduled_minutes(scheduled_start, scheduled_end)
    if worked is None:
        return None, None
    if sched is None:
        return worked, None
    return worked, max(0, sched - worked)


def _seconds_between_same_day(event_date: str, start_time: str, end_time: str) -> int | None:
    try:
        start_dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"{event_date} {end_time}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return int((end_dt - start_dt).total_seconds())


def _legacy_ensure_dtr_row(cur: sqlite3.Cursor, teacher_id: int, date: str) -> int:
    cur.execute(
        """
        SELECT id
        FROM dtr_logs
        WHERE teacher_id = ? AND date = ?
        """,
        (teacher_id, date),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        """
        INSERT INTO dtr_logs (teacher_id, date)
        VALUES (?, ?)
        """,
        (teacher_id, date),
    )
    return int(cur.lastrowid)


def _legacy_set_slot(cur: sqlite3.Cursor, *, log_id: int, slot: str, value: str) -> None:
    if slot not in {"am_in", "am_out", "pm_in", "pm_out"}:
        raise ValueError(f"Unexpected legacy slot: {slot}")
    cur.execute(
        f"""
        UPDATE dtr_logs
        SET {slot} = ?,
            event_time = NULL,
            status = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (value, log_id),
    )


def _sync_legacy_dtr_from_v2(
    cur: sqlite3.Cursor,
    *,
    decision_code: DecisionCode,
    teacher_id: int,
    event_date: str,
    event_time: str,
    scan_time: time,
) -> None:
    log_id = _legacy_ensure_dtr_row(cur, teacher_id, event_date)

    if decision_code == "TIME_IN_SET":
        slot = "am_in" if _in_am_window(scan_time) else "pm_in"
        _legacy_set_slot(cur, log_id=log_id, slot=slot, value=event_time)
        return

    if decision_code == "TIME_OUT_SET":
        slot = "am_out" if _in_am_window(scan_time) else "pm_out"
        _legacy_set_slot(cur, log_id=log_id, slot=slot, value=event_time)
        return

    if decision_code in {"OUTSIDE_SCHEDULE", "OUTSIDE_SCHEDULE_LUNCH"}:
        status_text = "Lunch break" if decision_code == "OUTSIDE_SCHEDULE_LUNCH" else "Outside shift hours"
        cur.execute(
            """
            UPDATE dtr_logs
            SET event_time = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (event_time, status_text, log_id),
        )


def _count_scan_attempts(cur: sqlite3.Cursor, *, teacher_id: int, date: str) -> int:
    cur.execute(
        """
        SELECT COUNT(1)
        FROM scan_events
        WHERE teacher_id = ? AND event_date = ?
        """,
        (teacher_id, date),
    )
    row = cur.fetchone()
    return int(row[0] or 0)


def run_attendance_maintenance_v2(
    *,
    now: datetime | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, int]:
    owns_conn = conn is None
    active_conn = conn or connect_db()
    ensure_attendance_v2_schema(active_conn)
    cur = active_conn.cursor()
    marker = now or datetime.now()

    try:
        auto_closed = _apply_auto_close_maintenance(cur=cur, now=marker, conn=active_conn)
        absent_marked = _apply_absence_maintenance(cur=cur, now=marker, conn=active_conn)
        if owns_conn:
            active_conn.commit()
        return {"auto_closed": auto_closed, "absent_marked": absent_marked}
    finally:
        if owns_conn:
            active_conn.close()


def _apply_auto_close_maintenance(
    *,
    cur: sqlite3.Cursor,
    now: datetime,
    conn: sqlite3.Connection,
) -> int:
    today = now.strftime("%Y-%m-%d")
    now_hms = now.strftime("%H:%M:%S")
    auto_close_cutoff_hms = ATTENDANCE_AUTO_CLOSE_CUTOFF.strftime("%H:%M:%S")
    system_source = "SystemAutoClose"

    cur.execute(
        """
        SELECT id, teacher_id, date, time_in, scheduled_start, scheduled_end
        FROM attendance_daily
        WHERE time_in IS NOT NULL
          AND time_out IS NULL
          AND (
              date < ?
              OR (date = ? AND ? >= ?)
          )
        """,
        (today, today, now_hms, auto_close_cutoff_hms),
    )
    rows = cur.fetchall()
    if not rows:
        return 0

    changed = 0
    for row_id, teacher_id, event_date, time_in, scheduled_start, scheduled_end in rows:
        final_time_out = str(scheduled_end or PM_END.strftime("%H:%M:%S"))
        worked_minutes, undertime_minutes = _compute_work_and_undertime(
            time_in=str(time_in),
            time_out=final_time_out,
            scheduled_start=str(scheduled_start) if scheduled_start else None,
            scheduled_end=str(scheduled_end) if scheduled_end else None,
        )
        remarks = f"Auto-closed at cutoff {auto_close_cutoff_hms}."

        cur.execute(
            """
            UPDATE attendance_daily
            SET time_out = ?,
                status = 'Auto-Closed',
                remarks = ?,
                worked_minutes = COALESCE(?, worked_minutes),
                undertime_minutes = COALESCE(?, undertime_minutes),
                auto_closed_at = CURRENT_TIMESTAMP,
                source = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (final_time_out, remarks, worked_minutes, undertime_minutes, system_source, row_id),
        )

        insert_scan_event_v2(
            decision_code="AUTO_CLOSED_SET",
            message=remarks,
            teacher_id=int(teacher_id),
            recognized_label=int(teacher_id),
            confidence=None,
            event_date=str(event_date),
            event_time=now_hms,
            source=system_source,
            request_id=f"auto_close:{event_date}:{teacher_id}:{final_time_out}",
            requires_review=True,
            dtr_record_id=int(row_id),
            payload_json=json.dumps(
                {
                    "time_out": final_time_out,
                    "scheduled_end": scheduled_end,
                }
            ),
            conn=conn,
        )
        changed += 1
    return changed


def _apply_absence_maintenance(
    *,
    cur: sqlite3.Cursor,
    now: datetime,
    conn: sqlite3.Connection,
) -> int:
    if now.time() < ATTENDANCE_ABSENCE_CUTOFF:
        return 0

    target_date = now.strftime("%Y-%m-%d")
    scheduled_start = AM_START.strftime("%H:%M:%S")
    scheduled_end = PM_END.strftime("%H:%M:%S")
    scheduled_minutes = _scheduled_minutes(scheduled_start, scheduled_end)
    system_source = "SystemAbsence"
    remarks = "No valid time-in before absence cutoff."

    cur.execute(
        """
        SELECT t.id
        FROM teachers t
        LEFT JOIN attendance_daily ad
          ON ad.teacher_id = t.id
         AND ad.date = ?
        WHERE ad.id IS NULL
        ORDER BY t.id ASC
        """,
        (target_date,),
    )
    missing_teachers = [int(row[0]) for row in cur.fetchall()]
    if not missing_teachers:
        return 0

    changed = 0
    for teacher_id in missing_teachers:
        cur.execute(
            """
            INSERT INTO attendance_daily (
                teacher_id,
                date,
                time_in,
                time_out,
                status,
                remarks,
                scan_attempts,
                source,
                scheduled_start,
                scheduled_end,
                grace_minutes,
                late_by_minutes,
                worked_minutes,
                undertime_minutes,
                absence_marked_at
            )
            VALUES (?, ?, NULL, NULL, 'Absent', ?, 0, ?, ?, ?, ?, 0, 0, ?, CURRENT_TIMESTAMP)
            """,
            (
                teacher_id,
                target_date,
                remarks,
                system_source,
                scheduled_start,
                scheduled_end,
                ATTENDANCE_GRACE_MINUTES,
                scheduled_minutes,
            ),
        )
        dtr_record_id = int(cur.lastrowid)

        insert_scan_event_v2(
            decision_code="ABSENCE_MARKED",
            message=remarks,
            teacher_id=teacher_id,
            recognized_label=teacher_id,
            confidence=None,
            event_date=target_date,
            event_time=ATTENDANCE_ABSENCE_CUTOFF.strftime("%H:%M:%S"),
            source=system_source,
            request_id=f"absence_marked:{target_date}:{teacher_id}",
            requires_review=True,
            dtr_record_id=dtr_record_id,
            payload_json=json.dumps(
                {
                    "scheduled_start": scheduled_start,
                    "scheduled_end": scheduled_end,
                    "cutoff": ATTENDANCE_ABSENCE_CUTOFF.strftime("%H:%M:%S"),
                }
            ),
            conn=conn,
        )
        changed += 1
    return changed


def _coerce_attendance_status(value: str | None) -> AttendanceStatus | None:
    allowed: set[str] = {"Present", "Late", "Absent", "Outside Hours", "Auto-Closed"}
    if value in allowed:
        return cast(AttendanceStatus, value)
    return None


def _build_scan_result(
    *,
    verified: bool,
    logged: bool,
    decision_code: DecisionCode,
    message: str,
    teacher_id: int | None,
    full_name: str | None,
    department: str | None,
    confidence: float | None,
    dtr_action: DtrAction,
    date: str,
    event_time: str,
    time_in: str | None = None,
    time_out: str | None = None,
    status: AttendanceStatus | None = None,
    remarks: str | None = None,
    late_by_minutes: int | None = None,
    worked_minutes: int | None = None,
    undertime_minutes: int | None = None,
    auto_closed: bool = False,
    scan_event_id: int = 0,
    dtr_record_id: int | None = None,
    scan_attempts_today: int = 0,
    requires_admin_review: bool = False,
    retry_after_seconds: int | None = None,
    request_id: str | None = None,
) -> AttendanceV2ScanResult:
    return {
        "verified": verified,
        "logged": logged,
        "decision_code": decision_code,
        "message": message,
        "teacher_id": teacher_id,
        "full_name": full_name,
        "department": department,
        "confidence": confidence,
        "dtr_action": dtr_action,
        "date": date,
        "event_time": event_time,
        "time_in": time_in,
        "time_out": time_out,
        "status": status,
        "remarks": remarks,
        "late_by_minutes": late_by_minutes,
        "worked_minutes": worked_minutes,
        "undertime_minutes": undertime_minutes,
        "auto_closed": auto_closed,
        "scan_event_id": scan_event_id,
        "dtr_record_id": dtr_record_id,
        "scan_attempts_today": scan_attempts_today,
        "requires_admin_review": requires_admin_review,
        "retry_after_seconds": retry_after_seconds,
        "request_id": request_id,
    }


def _decision_logged(decision_code: DecisionCode) -> bool:
    return decision_code in {"TIME_IN_SET", "TIME_OUT_SET"}


def _decision_verified(decision_code: DecisionCode) -> bool:
    return decision_code not in {
        "FACE_PENDING_CONFIRMATION",
        "FACE_LOW_CONFIDENCE",
        "FACE_NO_MATCH",
        "UNKNOWN_FACE_NOT_ENROLLED",
        "ERROR",
    }


def _result_from_existing_request(
    cur: sqlite3.Cursor,
    *,
    request_id: str,
    full_name: str | None,
    department: str | None,
) -> AttendanceV2ScanResult | None:
    cur.execute(
        """
        SELECT
            se.id,
            se.teacher_id,
            se.confidence,
            se.decision_code,
            se.message,
            se.event_date,
            se.event_time,
            se.requires_review,
            se.dtr_record_id,
            ad.time_in,
            ad.time_out,
            ad.status,
            ad.remarks,
            ad.scan_attempts,
            ad.late_by_minutes,
            ad.worked_minutes,
            ad.undertime_minutes,
            ad.auto_closed_at
        FROM scan_events se
        LEFT JOIN attendance_daily ad ON ad.id = se.dtr_record_id
        WHERE se.request_id = ?
        LIMIT 1
        """,
        (request_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    decision_code = str(row[3])
    if decision_code not in {
        "TIME_IN_SET",
        "TIME_OUT_SET",
        "AUTO_CLOSED_SET",
        "ABSENCE_MARKED",
        "OUTSIDE_SCHEDULE",
        "OUTSIDE_SCHEDULE_LUNCH",
        "DAY_COMPLETE",
        "FACE_PENDING_CONFIRMATION",
        "FACE_LOW_CONFIDENCE",
        "FACE_NO_MATCH",
        "UNKNOWN_FACE_NOT_ENROLLED",
        "DUPLICATE_IGNORED",
        "ERROR",
    }:
        decision_code = "ERROR"

    typed_decision = cast(DecisionCode, decision_code)
    dtr_action: DtrAction = "none"
    if typed_decision == "TIME_IN_SET":
        dtr_action = "time_in"
    elif typed_decision == "TIME_OUT_SET":
        dtr_action = "time_out"

    return _build_scan_result(
        verified=_decision_verified(typed_decision),
        logged=_decision_logged(typed_decision),
        decision_code=typed_decision,
        message=str(row[4] or ""),
        teacher_id=int(row[1]) if row[1] is not None else None,
        full_name=full_name,
        department=department,
        confidence=float(row[2]) if row[2] is not None else None,
        dtr_action=dtr_action,
        date=str(row[5]),
        event_time=str(row[6]),
        time_in=str(row[9]) if row[9] else None,
        time_out=str(row[10]) if row[10] else None,
        status=_coerce_attendance_status(str(row[11]) if row[11] else None),
        remarks=str(row[12]) if row[12] else None,
        late_by_minutes=int(row[14]) if row[14] is not None else None,
        worked_minutes=int(row[15]) if row[15] is not None else None,
        undertime_minutes=int(row[16]) if row[16] is not None else None,
        auto_closed=row[17] is not None,
        scan_event_id=int(row[0]),
        dtr_record_id=int(row[8]) if row[8] is not None else None,
        scan_attempts_today=int(row[13] or 0),
        requires_admin_review=bool(row[7]),
        retry_after_seconds=None,
        request_id=request_id,
    )


def process_attendance_scan_v2(
    *,
    teacher_id: int | None,
    full_name: str | None,
    department: str | None,
    confidence: float | None,
    scan_verified: bool,
    reason: str | None,
    event_date: str,
    event_time: str,
    source: str = "LiveFaceCapture",
    session_id: str | None = None,
    request_id: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> AttendanceV2ScanResult:
    """
    Main v2 attendance state-machine contract.

    Expected behavior:
    - Write scan audit event (`scan_events`) for every attempt.
    - Update `attendance_daily` when business rules allow.
    - Return API-ready decision payload.
    """
    owns_conn = conn is None
    active_conn = conn or connect_db()
    ensure_attendance_v2_schema(active_conn)
    cur = active_conn.cursor()
    run_attendance_maintenance_v2(conn=active_conn)

    event_date, event_time, scan_time = _normalize_event_datetime(event_date, event_time)
    reason_key = (reason or "").strip().lower()
    message_reason = reason_key or "no_match"

    if request_id:
        existing = _result_from_existing_request(
            cur,
            request_id=request_id,
            full_name=full_name,
            department=department,
        )
        if existing:
            return existing

    scan_event_id = 0
    dtr_record_id: int | None = None
    time_in: str | None = None
    time_out: str | None = None
    status: AttendanceStatus | None = None
    remarks: str | None = None
    late_by_minutes: int | None = None
    worked_minutes: int | None = None
    undertime_minutes: int | None = None
    auto_closed = False
    absence_marked = False
    requires_admin_review = False
    retry_after_seconds: int | None = None
    recognized_label = teacher_id
    safe_teacher_id = teacher_id
    decision_code: DecisionCode = "ERROR"
    decision_message = "Unhandled attendance state."
    logged = False
    dtr_action: DtrAction = "none"
    verified_output = scan_verified
    scan_attempts_today = 0

    try:
        # Verify teacher existence if an ID is present.
        teacher_exists = False
        if teacher_id is not None:
            cur.execute(
                """
                SELECT id
                FROM teachers
                WHERE id = ?
                """,
                (teacher_id,),
            )
            teacher_exists = cur.fetchone() is not None

        if not scan_verified:
            safe_teacher_id = teacher_id if teacher_exists else None
            if reason_key == "pending_confirmation":
                decision_code = "FACE_PENDING_CONFIRMATION"
                decision_message = "Face match pending additional confirmations."
            elif reason_key == "low_confidence":
                decision_code = "FACE_LOW_CONFIDENCE"
                decision_message = "Face match confidence is below strict threshold."
            elif reason_key == "unknown_face":
                decision_code = "UNKNOWN_FACE_NOT_ENROLLED"
                decision_message = "Face was recognized but the teacher is not enrolled."
                safe_teacher_id = None
                requires_admin_review = True
            else:
                decision_code = "FACE_NO_MATCH"
                decision_message = f"No face match: {message_reason}"

            scan_event_id = insert_scan_event_v2(
                decision_code=decision_code,
                message=decision_message,
                teacher_id=safe_teacher_id,
                recognized_label=recognized_label,
                confidence=confidence,
                event_date=event_date,
                event_time=event_time,
                source=source,
                session_id=session_id,
                request_id=request_id,
                requires_review=requires_admin_review,
                payload_json=json.dumps(
                    {
                        "scan_verified": False,
                        "reason": reason_key or None,
                    }
                ),
                conn=active_conn,
            )

            if safe_teacher_id is not None:
                scan_attempts_today = _count_scan_attempts(cur, teacher_id=safe_teacher_id, date=event_date)

            if owns_conn:
                active_conn.commit()

            return _build_scan_result(
                verified=False,
                logged=False,
                decision_code=decision_code,
                message=decision_message,
                teacher_id=teacher_id,
                full_name=full_name,
                department=department,
                confidence=confidence,
                dtr_action="none",
                date=event_date,
                event_time=event_time,
                status=None,
                remarks=reason_key or None,
                scan_event_id=scan_event_id,
                dtr_record_id=None,
                scan_attempts_today=scan_attempts_today,
                requires_admin_review=requires_admin_review,
                retry_after_seconds=None,
                request_id=request_id,
            )

        if teacher_id is None or not teacher_exists:
            decision_code = "UNKNOWN_FACE_NOT_ENROLLED"
            decision_message = "Verified scan received for an unknown teacher."
            requires_admin_review = True
            verified_output = False
            safe_teacher_id = None
            scan_event_id = insert_scan_event_v2(
                decision_code=decision_code,
                message=decision_message,
                teacher_id=None,
                recognized_label=recognized_label,
                confidence=confidence,
                event_date=event_date,
                event_time=event_time,
                source=source,
                session_id=session_id,
                request_id=request_id,
                requires_review=True,
                payload_json=json.dumps({"scan_verified": True, "reason": reason_key or None}),
                conn=active_conn,
            )
            if owns_conn:
                active_conn.commit()
            return _build_scan_result(
                verified=verified_output,
                logged=False,
                decision_code=decision_code,
                message=decision_message,
                teacher_id=teacher_id,
                full_name=full_name,
                department=department,
                confidence=confidence,
                dtr_action="none",
                date=event_date,
                event_time=event_time,
                status=None,
                remarks="unknown_teacher",
                scan_event_id=scan_event_id,
                dtr_record_id=None,
                scan_attempts_today=0,
                requires_admin_review=True,
                retry_after_seconds=None,
                request_id=request_id,
            )

        scheduled_start_hms = _hms(_shift_start_for_scan(scan_time))
        scheduled_end_hms = _hms(PM_END)
        dtr_record_id = get_or_create_attendance_daily_v2(
            teacher_id=teacher_id,
            date=event_date,
            source=source,
            scheduled_start=scheduled_start_hms,
            scheduled_end=scheduled_end_hms,
            grace_minutes=ATTENDANCE_GRACE_MINUTES,
            conn=active_conn,
        )

        cur.execute(
            """
            SELECT
                time_in,
                time_out,
                status,
                remarks,
                scheduled_start,
                scheduled_end,
                grace_minutes,
                late_by_minutes,
                worked_minutes,
                undertime_minutes,
                auto_closed_at,
                absence_marked_at
            FROM attendance_daily
            WHERE id = ?
            """,
            (dtr_record_id,),
        )
        row = cur.fetchone()
        time_in = str(row[0]) if row and row[0] else None
        time_out = str(row[1]) if row and row[1] else None
        status = _coerce_attendance_status(str(row[2]) if row and row[2] else "Absent") or "Absent"
        remarks = str(row[3]) if row and row[3] else None
        scheduled_start_hms = str(row[4]) if row and row[4] else scheduled_start_hms
        scheduled_end_hms = str(row[5]) if row and row[5] else scheduled_end_hms
        grace_minutes = int(row[6]) if row and row[6] is not None else ATTENDANCE_GRACE_MINUTES
        late_by_minutes = int(row[7]) if row and row[7] is not None else 0
        worked_minutes = int(row[8]) if row and row[8] is not None else None
        undertime_minutes = int(row[9]) if row and row[9] is not None else None
        auto_closed = bool(row[10]) if row else False
        absence_marked = bool(row[11]) if row else False

        in_working_hours = _in_am_window(scan_time) or _in_pm_window(scan_time)
        if time_in and time_out:
            decision_code = "DAY_COMPLETE"
            decision_message = "Attendance already complete for this day."
            logged = False
            dtr_action = "none"
            remarks = "Attendance already complete."

        elif not in_working_hours:
            scheduled_end_time = _coerce_clock_time(scheduled_end_hms) or PM_END
            can_outside_timeout = bool(time_in and not time_out and scan_time >= scheduled_end_time)
            if can_outside_timeout:
                elapsed_seconds = _seconds_between_same_day(event_date, time_in, event_time)
                if (
                    ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS > 0
                    and elapsed_seconds is not None
                    and elapsed_seconds < ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS
                ):
                    decision_code = "DUPLICATE_IGNORED"
                    decision_message = "Duplicate scan ignored; too soon after time-in."
                    logged = False
                    dtr_action = "none"
                    retry_after_seconds = ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS - elapsed_seconds
                else:
                    decision_code = "TIME_OUT_SET"
                    decision_message = "Time-out recorded outside shift hours."
                    requires_admin_review = True
                    logged = True
                    dtr_action = "time_out"
                    time_out = event_time
                    worked_minutes, undertime_minutes = _compute_work_and_undertime(
                        time_in=time_in,
                        time_out=time_out,
                        scheduled_start=scheduled_start_hms,
                        scheduled_end=scheduled_end_hms,
                    )
                    if status not in {"Present", "Late"}:
                        status = "Present"
                    remarks = decision_message
                    cur.execute(
                        """
                        UPDATE attendance_daily
                        SET time_out = ?,
                            status = ?,
                            remarks = ?,
                            source = ?,
                            worked_minutes = COALESCE(?, worked_minutes),
                            undertime_minutes = COALESCE(?, undertime_minutes),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            time_out,
                            status,
                            remarks,
                            source,
                            worked_minutes,
                            undertime_minutes,
                            dtr_record_id,
                        ),
                    )
            else:
                decision_code = "OUTSIDE_SCHEDULE_LUNCH" if _is_lunch_break(scan_time) else "OUTSIDE_SCHEDULE"
                decision_message = "Scan is during lunch break." if _is_lunch_break(scan_time) else "Scan is outside shift hours."
                requires_admin_review = True
                logged = False
                dtr_action = "none"

                next_status = status
                if not time_in and not time_out:
                    if status == "Absent" and absence_marked:
                        next_status = "Absent"
                    else:
                        next_status = "Outside Hours"
                cur.execute(
                    """
                    UPDATE attendance_daily
                    SET status = ?,
                        remarks = ?,
                        source = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (next_status, decision_message, source, dtr_record_id),
                )
                status = next_status
                remarks = decision_message

        elif not time_in:
            decision_code = "TIME_IN_SET"
            decision_message = "Time-in recorded."
            logged = True
            dtr_action = "time_in"
            status, late_by_minutes = _time_in_status(
                scan_time,
                scheduled_start=_coerce_clock_time(scheduled_start_hms) or _shift_start_for_scan(scan_time),
                grace_minutes=grace_minutes,
            )
            time_in = event_time
            remarks = None
            cur.execute(
                """
                UPDATE attendance_daily
                SET time_in = ?,
                    status = ?,
                    remarks = NULL,
                    source = ?,
                    late_by_minutes = ?,
                    worked_minutes = NULL,
                    undertime_minutes = NULL,
                    auto_closed_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (time_in, status, source, late_by_minutes or 0, dtr_record_id),
            )

        elif not time_out:
            elapsed_seconds = _seconds_between_same_day(event_date, time_in, event_time)
            if (
                ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS > 0
                and elapsed_seconds is not None
                and elapsed_seconds < ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS
            ):
                decision_code = "DUPLICATE_IGNORED"
                decision_message = "Duplicate scan ignored; too soon after time-in."
                logged = False
                dtr_action = "none"
                retry_after_seconds = ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS - elapsed_seconds
            else:
                decision_code = "TIME_OUT_SET"
                decision_message = "Time-out recorded."
                logged = True
                dtr_action = "time_out"
                time_out = event_time
                worked_minutes, undertime_minutes = _compute_work_and_undertime(
                    time_in=time_in,
                    time_out=time_out,
                    scheduled_start=scheduled_start_hms,
                    scheduled_end=scheduled_end_hms,
                )
                if status not in {"Present", "Late"}:
                    status = "Present"
                remarks = None
                cur.execute(
                    """
                    UPDATE attendance_daily
                    SET time_out = ?,
                        status = ?,
                        remarks = NULL,
                        source = ?,
                        worked_minutes = COALESCE(?, worked_minutes),
                        undertime_minutes = COALESCE(?, undertime_minutes),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (time_out, status, source, worked_minutes, undertime_minutes, dtr_record_id),
                )

        else:
            decision_code = "DAY_COMPLETE"
            decision_message = "Attendance already complete for this day."
            logged = False
            dtr_action = "none"
            remarks = "Attendance already complete."

        if decision_code in {"TIME_IN_SET", "TIME_OUT_SET", "OUTSIDE_SCHEDULE", "OUTSIDE_SCHEDULE_LUNCH"}:
            _sync_legacy_dtr_from_v2(
                cur,
                decision_code=decision_code,
                teacher_id=teacher_id,
                event_date=event_date,
                event_time=event_time,
                scan_time=scan_time,
            )

        scan_event_id = insert_scan_event_v2(
            decision_code=decision_code,
            message=decision_message,
            teacher_id=teacher_id,
            recognized_label=recognized_label,
            confidence=confidence,
            event_date=event_date,
            event_time=event_time,
            source=source,
            session_id=session_id,
            request_id=request_id,
            requires_review=requires_admin_review,
            dtr_record_id=dtr_record_id,
            payload_json=json.dumps(
                {
                    "scan_verified": scan_verified,
                    "reason": reason_key or None,
                    "dtr_action": dtr_action,
                }
            ),
            conn=active_conn,
        )

        scan_attempts_today = _count_scan_attempts(cur, teacher_id=teacher_id, date=event_date)
        cur.execute(
            """
            UPDATE attendance_daily
            SET scan_attempts = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (scan_attempts_today, dtr_record_id),
        )

        cur.execute(
            """
            SELECT
                time_in,
                time_out,
                status,
                remarks,
                late_by_minutes,
                worked_minutes,
                undertime_minutes,
                auto_closed_at
            FROM attendance_daily
            WHERE id = ?
            """,
            (dtr_record_id,),
        )
        row = cur.fetchone()
        time_in = str(row[0]) if row and row[0] else None
        time_out = str(row[1]) if row and row[1] else None
        status = _coerce_attendance_status(str(row[2]) if row and row[2] else None)
        remarks = str(row[3]) if row and row[3] else remarks
        late_by_minutes = int(row[4]) if row and row[4] is not None else late_by_minutes
        worked_minutes = int(row[5]) if row and row[5] is not None else worked_minutes
        undertime_minutes = int(row[6]) if row and row[6] is not None else undertime_minutes
        auto_closed = bool(row[7]) if row and row[7] else False

        if owns_conn:
            active_conn.commit()

        return _build_scan_result(
            verified=verified_output,
            logged=logged,
            decision_code=decision_code,
            message=decision_message,
            teacher_id=teacher_id,
            full_name=full_name,
            department=department,
            confidence=confidence,
            dtr_action=dtr_action,
            date=event_date,
            event_time=event_time,
            time_in=time_in,
            time_out=time_out,
            status=status,
            remarks=remarks,
            late_by_minutes=late_by_minutes,
            worked_minutes=worked_minutes,
            undertime_minutes=undertime_minutes,
            auto_closed=auto_closed,
            scan_event_id=scan_event_id,
            dtr_record_id=dtr_record_id,
            scan_attempts_today=scan_attempts_today,
            requires_admin_review=requires_admin_review,
            retry_after_seconds=retry_after_seconds,
            request_id=request_id,
        )
    except Exception as exc:
        if owns_conn:
            active_conn.rollback()

        error_message = f"Attendance scan processing failed: {exc}"
        try:
            scan_event_id = insert_scan_event_v2(
                decision_code="ERROR",
                message=error_message,
                teacher_id=None,
                recognized_label=recognized_label,
                confidence=confidence,
                event_date=event_date,
                event_time=event_time,
                source=source,
                session_id=session_id,
                request_id=request_id,
                requires_review=True,
                error_code=exc.__class__.__name__,
                payload_json=json.dumps(
                    {
                        "scan_verified": scan_verified,
                        "reason": reason_key or None,
                    }
                ),
                conn=active_conn,
            )
            if owns_conn:
                active_conn.commit()
        except Exception:
            scan_event_id = 0

        return _build_scan_result(
            verified=False,
            logged=False,
            decision_code="ERROR",
            message=error_message,
            teacher_id=teacher_id,
            full_name=full_name,
            department=department,
            confidence=confidence,
            dtr_action="none",
            date=event_date,
            event_time=event_time,
            time_in=None,
            time_out=None,
            status=None,
            remarks=reason_key or None,
            scan_event_id=scan_event_id,
            dtr_record_id=dtr_record_id,
            scan_attempts_today=0,
            requires_admin_review=True,
            retry_after_seconds=None,
            request_id=request_id,
        )
    finally:
        if owns_conn:
            active_conn.close()


def get_scan_events_v2(
    *,
    teacher_id: int | None = None,
    date: str | None = None,
    decision_code: DecisionCode | None = None,
    requires_review: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Admin query contract for scan audit history.
    """
    where_sql, params = _build_scan_events_where_clause(
        teacher_id=teacher_id,
        date=date,
        decision_code=decision_code,
        requires_review=requires_review,
    )

    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    cur = conn.cursor()

    safe_limit = max(1, min(int(limit), 500))
    safe_offset = max(0, int(offset))

    query = f"""
        SELECT
            se.id,
            se.teacher_id,
            t.full_name,
            t.department,
            se.recognized_label,
            se.confidence,
            se.decision_code,
            se.message,
            se.captured_at,
            se.event_date,
            se.event_time,
            se.source,
            se.session_id,
            se.request_id,
            se.requires_review,
            se.error_code,
            se.dtr_record_id,
            se.payload_json
        FROM scan_events se
        LEFT JOIN teachers t ON t.id = se.teacher_id
        WHERE {where_sql}
        ORDER BY se.captured_at DESC, se.id DESC
        LIMIT ?
        OFFSET ?
    """
    params.extend([safe_limit, safe_offset])

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": row[0],
                "teacher_id": row[1],
                "full_name": row[2],
                "department": row[3],
                "recognized_label": row[4],
                "confidence": row[5],
                "decision_code": row[6],
                "message": row[7],
                "captured_at": row[8],
                "event_date": row[9],
                "event_time": row[10],
                "source": row[11],
                "session_id": row[12],
                "request_id": row[13],
                "requires_review": bool(row[14]),
                "error_code": row[15],
                "dtr_record_id": row[16],
                "payload_json": row[17],
            }
        )
    return out


def get_scan_events_total_v2(
    *,
    teacher_id: int | None = None,
    date: str | None = None,
    decision_code: DecisionCode | None = None,
    requires_review: bool | None = None,
) -> int:
    where_sql, params = _build_scan_events_where_clause(
        teacher_id=teacher_id,
        date=date,
        decision_code=decision_code,
        requires_review=requires_review,
    )

    conn = connect_db()
    ensure_attendance_v2_schema(conn)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT COUNT(1)
        FROM scan_events se
        WHERE {where_sql}
        """,
        params,
    )
    row = cur.fetchone()
    conn.close()
    return int(row[0] or 0) if row else 0


def _build_scan_events_where_clause(
    *,
    teacher_id: int | None = None,
    date: str | None = None,
    decision_code: DecisionCode | None = None,
    requires_review: bool | None = None,
) -> tuple[str, list[Any]]:
    where = ["1=1"]
    params: list[Any] = []

    if teacher_id is not None:
        where.append("se.teacher_id = ?")
        params.append(teacher_id)
    if date is not None:
        where.append("se.event_date = ?")
        params.append(date)
    if decision_code is not None:
        where.append("se.decision_code = ?")
        params.append(decision_code)
    if requires_review is not None:
        where.append("se.requires_review = ?")
        params.append(1 if requires_review else 0)

    return " AND ".join(where), params
