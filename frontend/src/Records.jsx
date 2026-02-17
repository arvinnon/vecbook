import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteAttendanceLog, fetchAttendance, fetchSummary, resetAttendance } from "./api";
import ConfirmModal from "./ConfirmModal";
import { useTheme } from "./ThemeProvider";

function formatTo12Hour(value) {
  if (!value) return "";
  const raw = String(value).trim();
  if (!raw) return "";
  if (/[AP]M/i.test(raw)) return raw;

  const m = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return raw;

  let hh = Number(m[1]);
  const mm = m[2];
  const ss = m[3] || "00";
  const suffix = hh >= 12 ? "PM" : "AM";
  hh %= 12;
  if (hh === 0) hh = 12;
  return `${String(hh).padStart(2, "0")}:${mm}:${ss} ${suffix}`;
}

function formatLastScan(row) {
  if (!row || row.time_in || row.time_out) return "";
  return formatTo12Hour(row.last_scan_time);
}

export default function Records() {
  const { t, mode, toggle } = useTheme();

  const [date, setDate] = useState("");
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [toast, setToast] = useState({ type: "", msg: "" });

  async function load(selectedDate = date) {
    const filterDate = typeof selectedDate === "string" ? selectedDate : date;
    try {
      const data = await fetchAttendance(filterDate || null);
      setRows(data);
      if (filterDate) setSummary(await fetchSummary(filterDate));
      else setSummary(null);
    } catch (e) {
      setRows([]);
      setSummary(null);
      setToast({ type: "error", msg: e.message || "Failed to load attendance." });
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function doReset() {
    setResetLoading(true);
    setToast({ type: "", msg: "" });
    try {
      const res = await resetAttendance();
      setConfirmOpen(false);
      setDate("");
      await load("");
      setToast({ type: "success", msg: res.message || "Attendance logs cleared." });
    } catch (e) {
      setToast({ type: "error", msg: e.message });
    } finally {
      setResetLoading(false);
    }
  }

  async function doDeleteLog() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    setToast({ type: "", msg: "" });
    try {
      await deleteAttendanceLog(deleteTarget);
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
      await load();
      setToast({ type: "success", msg: "Log entry deleted." });
    } catch (e) {
      setToast({ type: "error", msg: e.message });
    } finally {
      setDeleteLoading(false);
    }
  }

  function doPrint() {
    window.print();
  }

  const cardShadow = t.shadow;
  const rowBorder = t.rowBorder;

  return (
    <div style={{ background: t.bg, minHeight: "100vh", color: t.text }}>
      <header
        className="no-print"
        style={{
          background: t.header,
          color: t.headerText,
          padding: 18,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}
      >
        <h2 style={{ margin: 0 }}>Attendance Records</h2>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={toggle}
            style={{
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.25)",
              background: "rgba(255,255,255,0.12)",
              color: "white",
              fontWeight: 900,
              cursor: "pointer",
            }}
            title="Toggle theme"
          >
            {mode === "light" ? "\u{1F319} Dark" : "\u2600\uFE0F Light"}
          </button>

          <Link to="/home" style={{ color: "white", fontWeight: 700, textDecoration: "none" }}>
            Back
          </Link>
        </div>
      </header>

      <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
        {/* Filters / Summary */}
        <div
          className="no-print"
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 16,
            boxShadow: cardShadow,
            border: `1px solid ${t.border}`,
            marginBottom: 14,
          }}
        >
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <input
              value={date}
              onChange={(e) => setDate(e.target.value)}
              placeholder="YYYY-MM-DD"
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                outline: "none",
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 800,
                minWidth: 160,
              }}
            />

            <button
              onClick={load}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: t.primary,
                color: t.primaryText,
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Filter
            </button>

            <button
              onClick={doPrint}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: t.success,
                color: t.successText,
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
              }}
              title="Print attendance report"
            >
              {"\u{1F5A8} Print"}
            </button>

            {/* Reset Button */}
            <button
              onClick={() => setConfirmOpen(true)}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: t.danger,
                color: t.dangerText,
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Reset Logs
            </button>

            {summary && (
              <div style={{ fontWeight: 900, color: t.text }}>
                Total: {summary.total} | On-Time: {summary.on_time} | Late: {summary.late}
              </div>
            )}
          </div>

          {/* toast */}
          {toast.msg && (
            <div
              style={{
                marginTop: 12,
                padding: 12,
                borderRadius: 12,
                background: toast.type === "success" ? t.successBg : t.errorBg,
                border: `1px solid ${t.border}`,
              }}
            >
              <b style={{ color: toast.type === "success" ? t.successText : t.errorText }}>
                {toast.type === "success" ? "Success: " : "Error: "}
              </b>
              <span style={{ color: t.text }}>{toast.msg}</span>
            </div>
          )}
        </div>

     
        <div className="print-area">
          <div className="print-only" style={{ marginBottom: 14 }}>
            <h2 style={{ margin: 0 }}>Attendance Records</h2>
            <div style={{ marginTop: 6, color: "#111827" }}>
              {date ? `Date Filter: ${date}` : "All Dates"}{" "}
              {summary ? `| Total: ${summary.total} | On-Time: ${summary.on_time} | Late: ${summary.late}` : ""}
            </div>
          </div>

          <div
            style={{
              background: t.card,
              borderRadius: 18,
              padding: 16,
              boxShadow: cardShadow,
              border: `1px solid ${t.border}`,
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Name", "Department", "Date", "Time In", "Time Out", "Last Scan", "Status", "Actions"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: 10,
                        borderBottom: `1px solid ${t.border}`,
                        color: t.text,
                        fontWeight: 900,
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.full_name}</td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.department}</td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.date}</td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                      {formatTo12Hour(r.time_in)}
                    </td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                      {formatTo12Hour(r.time_out)}
                    </td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                      {formatLastScan(r)}
                    </td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.status}</td>
                    <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                      <button
                        onClick={() => {
                          setDeleteTarget(r.id);
                          setDeleteConfirmOpen(true);
                        }}
                        style={{
                          padding: "6px 10px",
                          borderRadius: 10,
                          border: "1px solid #FCA5A5",
                          background: "transparent",
                          color: t.dangerText,
                          fontWeight: 900,
                          cursor: "pointer",
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}

                {rows.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{ padding: 14, color: t.muted }}>
                      No records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        open={confirmOpen}
        title="Reset attendance logs?"
        message="This will permanently delete ALL attendance records. This action cannot be undone."
        confirmText="Yes, reset"
        cancelText="Cancel"
        danger
        loading={resetLoading}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={doReset}
      />

      <ConfirmModal
        open={deleteConfirmOpen}
        title="Delete this log entry?"
        message="This will permanently delete the selected log entry."
        confirmText="Yes, delete"
        cancelText="Cancel"
        danger
        loading={deleteLoading}
        onCancel={() => {
          setDeleteConfirmOpen(false);
          setDeleteTarget(null);
        }}
        onConfirm={doDeleteLog}
      />
    </div>
  );
}
