import sqlite3
from datetime import datetime, time

from backend.config import AM_END, AM_START, DB_PATH, PM_END, PM_START


def connect_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    # recommended with FK tables
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


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
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        UNIQUE(teacher_id, date)
    )
    """)

    # Drop legacy unused table if present.
    cursor.execute("DROP TABLE IF EXISTS face_embeddings;")

    # ✅ Migration for older DB
    try:
        cursor.execute("ALTER TABLE dtr_logs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    except sqlite3.OperationalError:
        pass

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
# ✅ DTR Punch Logic
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


def get_teacher_dtr_month(teacher_id: int, month: str):
    """
    month = "YYYY-MM"
    returns list of rows:
      (date, am_in, am_out, pm_in, pm_out)
    """
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, am_in, am_out, pm_in, pm_out
        FROM dtr_logs
        WHERE teacher_id=? AND date LIKE ?
        ORDER BY date ASC
    """, (teacher_id, f"{month}-%"))
    rows = cur.fetchall()
    conn.close()
    return rows


# -----------------------------
# Attendance list + summary (uses DTR AM IN)
# -----------------------------
def get_attendance_records(date=None):
    conn = connect_db()
    cur = conn.cursor()

    if date:
        cur.execute("""
            SELECT d.id, t.full_name, t.department, d.date, d.am_in, d.am_out, d.pm_in, d.pm_out
            FROM dtr_logs d
            JOIN teachers t ON d.teacher_id = t.id
            WHERE d.date = ? AND (d.am_in IS NOT NULL OR d.pm_in IS NOT NULL)
            ORDER BY COALESCE(d.am_in, d.pm_in)
        """, (date,))
    else:
        cur.execute("""
            SELECT d.id, t.full_name, t.department, d.date, d.am_in, d.am_out, d.pm_in, d.pm_out
            FROM dtr_logs d
            JOIN teachers t ON d.teacher_id = t.id
            WHERE d.am_in IS NOT NULL OR d.pm_in IS NOT NULL
            ORDER BY d.date DESC, COALESCE(d.am_in, d.pm_in) ASC
        """)

    rows = cur.fetchall()
    conn.close()

    # attach On-Time/Late based on 8:00 cutoff
    out = []
    cutoff_am = AM_START
    cutoff_pm = PM_START
    for log_id, full_name, department, dt, am_in, am_out, pm_in, pm_out in rows:
        time_in = am_in or pm_in
        time_out = pm_out or am_out
        try:
            if am_in:
                hh, mm, ss = [int(x) for x in am_in.split(":")]
                st = "On-Time" if time(hh, mm, ss) <= cutoff_am else "Late"
            elif pm_in:
                hh, mm, ss = [int(x) for x in pm_in.split(":")]
                st = "On-Time" if time(hh, mm, ss) <= cutoff_pm else "Late"
            else:
                st = "Recorded"
        except Exception:
            st = "Recorded"
        out.append((log_id, full_name, department, dt, time_in, time_out, st))
    return out


def get_daily_summary(date):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT am_in, pm_in
        FROM dtr_logs
        WHERE date = ? AND (am_in IS NOT NULL OR pm_in IS NOT NULL)
    """, (date,))
    times = cur.fetchall()
    conn.close()

    total = len(times)
    cutoff_am = AM_START
    cutoff_pm = PM_START
    on_time = 0
    late = 0

    for am_in, pm_in in times:
        try:
            if am_in:
                hh, mm, ss = [int(x) for x in am_in.split(":")]
                if time(hh, mm, ss) <= cutoff_am:
                    on_time += 1
                else:
                    late += 1
            elif pm_in:
                hh, mm, ss = [int(x) for x in pm_in.split(":")]
                if time(hh, mm, ss) <= cutoff_pm:
                    on_time += 1
                else:
                    late += 1
        except Exception:
            pass

    return {"total": total, "on_time": on_time, "late": late}


# -----------------------------
# Resets
# -----------------------------
def clear_attendance():
    conn = connect_db()
    cur = conn.cursor()

    # ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dtr_logs'")
    if not cur.fetchone():
        conn.close()
        return False

    cur.execute("DELETE FROM dtr_logs;")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='dtr_logs';")
    conn.commit()
    conn.close()
    return True


def clear_all_tables():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM dtr_logs;")
    cur.execute("DELETE FROM teachers;")

    cur.execute("DELETE FROM sqlite_sequence WHERE name='dtr_logs';")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='teachers';")

    conn.commit()
    conn.close()


def delete_dtr_log(log_id: int) -> bool:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dtr_logs WHERE id = ?", (log_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute("DELETE FROM dtr_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True
