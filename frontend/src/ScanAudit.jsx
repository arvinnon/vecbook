import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchScanEvents } from "./api";
import { useTheme } from "./ThemeProvider";

const DECISION_OPTIONS = [
  "",
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
];

function formatCapturedAt(value) {
  if (!value) return "-";
  const raw = String(value).trim();
  if (!raw) return "-";
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const withZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const parsed = new Date(withZone);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatConfidence(value) {
  if (value == null || value === "") return "-";
  const n = Number(value);
  if (Number.isNaN(n)) return "-";
  return n.toFixed(2);
}

export default function ScanAudit() {
  const { t, mode, toggle } = useTheme();
  const [date, setDate] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [decisionCode, setDecisionCode] = useState("");
  const [requiresReview, setRequiresReview] = useState("");
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const res = await fetchScanEvents({
        date: date || undefined,
        teacher_id: teacherId || undefined,
        decision_code: decisionCode || undefined,
        requires_review: requiresReview,
        limit: 200,
        offset: 0,
      });
      setRows(res.rows || []);
      setTotal(res.total || 0);
    } catch (e) {
      setRows([]);
      setTotal(0);
      setErr(e.message || "Failed to load scan events.");
    } finally {
      setLoading(false);
    }
  }

  function resetFilters() {
    setDate("");
    setTeacherId("");
    setDecisionCode("");
    setRequiresReview("");
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rowBorder = mode === "light" ? "#F3F4F6" : "rgba(255,255,255,0.08)";

  return (
    <div style={{ background: t.bg, minHeight: "100vh", color: t.text }}>
      <header
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
        <h2 style={{ margin: 0 }}>Scan Audit Logs</h2>
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

      <div style={{ padding: 24, maxWidth: 1300, margin: "0 auto" }}>
        <div
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 16,
            border: `1px solid ${t.border}`,
            boxShadow: t.shadow,
            marginBottom: 16,
          }}
        >
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 700,
              }}
            />
            <input
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
              placeholder="Teacher ID"
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 700,
              }}
            />
            <select
              value={decisionCode}
              onChange={(e) => setDecisionCode(e.target.value)}
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 700,
              }}
            >
              <option value="">All Decisions</option>
              {DECISION_OPTIONS.filter(Boolean).map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
            <select
              value={requiresReview}
              onChange={(e) => setRequiresReview(e.target.value)}
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 700,
              }}
            >
              <option value="">All Review Flags</option>
              <option value="true">Requires Review</option>
              <option value="false">No Review Needed</option>
            </select>
            <button
              onClick={load}
              disabled={loading}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: t.primary,
                color: t.primaryText,
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "Loading..." : "Apply Filters"}
            </button>
            <button
              onClick={resetFilters}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: "transparent",
                color: t.text,
                border: `1px solid ${t.border}`,
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Reset Filters
            </button>
          </div>

          <div style={{ marginTop: 10, fontWeight: 800, color: t.muted }}>
            Showing <b style={{ color: t.text }}>{rows.length}</b> of{" "}
            <b style={{ color: t.text }}>{total}</b> events
          </div>

          {err && (
            <div style={{ marginTop: 10, color: t.dangerText, fontWeight: 900 }}>
              {err}
            </div>
          )}
        </div>

        <div
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 16,
            border: `1px solid ${t.border}`,
            boxShadow: t.shadow,
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {[
                  "Captured At",
                  "Teacher",
                  "Department",
                  "Date",
                  "Time",
                  "Decision",
                  "Confidence",
                  "Review",
                  "Message",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: 10,
                      borderBottom: `1px solid ${t.border}`,
                      color: t.text,
                      fontWeight: 900,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {formatCapturedAt(r.captured_at)}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.full_name || (r.teacher_id ? `Teacher ID ${r.teacher_id}` : "Unknown")}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.department || "-"}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.event_date}</td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.event_time}</td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r.decision_code}</td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {formatConfidence(r.confidence)}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.requires_review ? "Yes" : "No"}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.message || "-"}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan="9" style={{ padding: 14, color: t.muted }}>
                    No scan events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
