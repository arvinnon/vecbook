BEGIN TRANSACTION;

-- -------------------------------------
-- attendance_daily: 1 row / teacher / day
-- -------------------------------------
CREATE TABLE IF NOT EXISTS attendance_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    date TEXT NOT NULL,                          -- YYYY-MM-DD
    time_in TEXT,                                -- HH:MM:SS
    time_out TEXT,                               -- HH:MM:SS
    status TEXT NOT NULL DEFAULT 'Absent' CHECK (
        status IN ('Present', 'Late', 'Absent', 'Outside Hours', 'Auto-Closed')
    ),
    remarks TEXT,
    scan_attempts INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'LiveFaceCapture',
    scheduled_start TEXT,
    scheduled_end TEXT,
    grace_minutes INTEGER NOT NULL DEFAULT 10,
    late_by_minutes INTEGER NOT NULL DEFAULT 0,
    worked_minutes INTEGER,
    undertime_minutes INTEGER,
    auto_closed_at TIMESTAMP,
    absence_marked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (teacher_id, date),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS trg_attendance_daily_updated_at
AFTER UPDATE ON attendance_daily
FOR EACH ROW
BEGIN
    UPDATE attendance_daily
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;

-- -------------------------------------
-- scan_events: append-only scan audit trail
-- -------------------------------------
CREATE TABLE IF NOT EXISTS scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER,                          -- nullable for unknown/failed
    recognized_label INTEGER,                    -- model label when available
    confidence REAL,
    decision_code TEXT NOT NULL,                 -- TIME_IN_SET, OUTSIDE_SCHEDULE, etc.
    message TEXT,
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_date TEXT NOT NULL,                    -- YYYY-MM-DD
    event_time TEXT NOT NULL,                    -- HH:MM:SS
    source TEXT NOT NULL DEFAULT 'LiveFaceCapture',
    session_id TEXT,
    request_id TEXT,                             -- idempotency key
    requires_review INTEGER NOT NULL DEFAULT 0 CHECK (requires_review IN (0, 1)),
    error_code TEXT,
    dtr_record_id INTEGER,                       -- attendance_daily.id
    payload_json TEXT,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL,
    FOREIGN KEY (dtr_record_id) REFERENCES attendance_daily(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_attendance_daily_date ON attendance_daily(date);
CREATE INDEX IF NOT EXISTS idx_attendance_daily_status ON attendance_daily(status);
CREATE INDEX IF NOT EXISTS idx_scan_events_teacher_date ON scan_events(teacher_id, event_date);
CREATE INDEX IF NOT EXISTS idx_scan_events_decision_time ON scan_events(decision_code, captured_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_events_request_id
ON scan_events(request_id) WHERE request_id IS NOT NULL;

-- -------------------------------------
-- Backfill from legacy dtr_logs (safe, idempotent)
-- -------------------------------------
INSERT INTO attendance_daily (
    teacher_id, date, time_in, time_out, status, remarks, scan_attempts, source,
    scheduled_start, scheduled_end, grace_minutes, late_by_minutes,
    worked_minutes, undertime_minutes, auto_closed_at, absence_marked_at,
    created_at, updated_at
)
SELECT
    d.teacher_id,
    d.date,
    COALESCE(d.am_in, d.pm_in) AS time_in,
    COALESCE(d.pm_out, d.am_out) AS time_out,
    CASE
        WHEN d.status IN ('Lunch break', 'Outside shift hours') THEN 'Outside Hours'
        WHEN COALESCE(d.am_in, d.pm_in) IS NOT NULL THEN 'Present'
        ELSE 'Absent'
    END AS status,
    d.status AS remarks,
    0,
    'LiveFaceCapture',
    '07:30:00',
    '17:00:00',
    10,
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    COALESCE(d.updated_at, CURRENT_TIMESTAMP),
    COALESCE(d.updated_at, CURRENT_TIMESTAMP)
FROM dtr_logs d
WHERE 1 = 1
ON CONFLICT(teacher_id, date) DO UPDATE SET
    time_in = COALESCE(excluded.time_in, attendance_daily.time_in),
    time_out = COALESCE(excluded.time_out, attendance_daily.time_out),
    remarks = COALESCE(attendance_daily.remarks, excluded.remarks),
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO scan_events (
    teacher_id, recognized_label, confidence, decision_code, message, captured_at,
    event_date, event_time, source, requires_review, dtr_record_id, payload_json
)
SELECT
    d.teacher_id,
    d.teacher_id,
    NULL,
    CASE
        WHEN d.status = 'Lunch break' THEN 'OUTSIDE_SCHEDULE_LUNCH'
        WHEN d.status = 'Outside shift hours' THEN 'OUTSIDE_SCHEDULE'
        WHEN COALESCE(d.pm_out, d.am_out) IS NOT NULL THEN 'TIME_OUT_SET'
        WHEN COALESCE(d.am_in, d.pm_in) IS NOT NULL THEN 'TIME_IN_SET'
        ELSE 'MIGRATED'
    END AS decision_code,
    COALESCE(d.status, 'Migrated from legacy dtr_logs'),
    COALESCE(d.updated_at, CURRENT_TIMESTAMP),
    d.date,
    COALESCE(d.event_time, d.pm_out, d.am_out, d.pm_in, d.am_in, '00:00:00'),
    'LiveFaceCapture',
    CASE WHEN d.status IN ('Lunch break', 'Outside shift hours') THEN 1 ELSE 0 END,
    ad.id,
    'legacy_dtr_log_id=' || CAST(d.id AS TEXT)
FROM dtr_logs d
LEFT JOIN attendance_daily ad
    ON ad.teacher_id = d.teacher_id
   AND ad.date = d.date;

UPDATE attendance_daily
SET scan_attempts = (
    SELECT COUNT(1)
    FROM scan_events se
    WHERE se.teacher_id = attendance_daily.teacher_id
      AND se.event_date = attendance_daily.date
);

COMMIT;
