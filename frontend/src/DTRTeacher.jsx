import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTeacherDTR } from "./api";
import { useTheme } from "./ThemeProvider";

function monthNow() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mm}`;
}

export default function TeacherDTR() {
  const { id } = useParams();
  const { t, mode, toggle } = useTheme();

  const [month, setMonth] = useState(monthNow());
  const [teacher, setTeacher] = useState(null);
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const res = await fetchTeacherDTR(id, month);
      setTeacher(res.teacher);
      setRows(res.rows || []);
    } catch (e) {
      setErr(e.message || "Failed to load DTR.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month]);

  const mapByDate = useMemo(() => {
    const m = new Map();
    rows.forEach((r) => m.set(r.date, r));
    return m;
  }, [rows]);

  // Build full month days (1..last day)
  const days = useMemo(() => {
    const [yy, mm] = month.split("-").map(Number);
    const last = new Date(yy, mm, 0).getDate(); // mm is 1-based but JS months are 0-based in constructor trick
    const out = [];
    for (let day = 1; day <= last; day++) {
      const dd = String(day).padStart(2, "0");
      out.push(`${month}-${dd}`);
    }
    return out;
  }, [month]);

  function doPrint() {
    window.print();
  }

  const cardShadow = t.shadow;
  const rowBorder = t.rowBorder;

  return (
    <div style={{ background: t.bg, minHeight: "100vh", color: t.text }}>
      {/* header hidden in print */}
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
        <h2 style={{ margin: 0 }}>Daily Time Record</h2>

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

          <Link to="/teachers" style={{ color: "white", fontWeight: 700, textDecoration: "none" }}>
            Back
          </Link>
        </div>
      </header>

      <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
        {/* top controls */}
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
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              style={{
                padding: 10,
                borderRadius: 10,
                border: `1px solid ${t.border}`,
                outline: "none",
                background: t.inputBg,
                color: t.inputText,
                fontWeight: 800,
                minWidth: 180,
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
              Load
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
            >
              {"\u{1F5A8} Print"}
            </button>
          </div>

          {teacher && (
            <div style={{ marginTop: 10, color: t.muted, fontWeight: 800 }}>
              <b style={{ color: t.text }}>{teacher.full_name}</b> | {teacher.department} |{" "}
              <span style={{ opacity: 0.9 }}>ID: {teacher.employee_id}</span>
            </div>
          )}

          {err && (
            <div style={{ marginTop: 10, color: t.dangerText, fontWeight: 900 }}>
              {err}
            </div>
          )}
        </div>

        {/* PRINT AREA */}
        <div className="print-area">
          {/* print header only */}
          <div className="print-only" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Daily Time Record</h2>
            {teacher && (
              <div style={{ marginTop: 6 }}>
                <b>{teacher.full_name}</b> | {teacher.department} | ID: {teacher.employee_id} <br />
                Month: {month}
              </div>
            )}
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
                  {["Day", "AM In", "AM Out", "PM In", "PM Out"].map((h) => (
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
                {days.map((d) => {
                  const r = mapByDate.get(d);
                  const day = d.split("-")[2];
                  return (
                    <tr key={d}>
                      <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}`, fontWeight: 900 }}>
                        {day}
                      </td>
                      <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r?.am_in || ""}</td>
                      <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r?.am_out || ""}</td>
                      <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r?.pm_in || ""}</td>
                      <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>{r?.pm_out || ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
