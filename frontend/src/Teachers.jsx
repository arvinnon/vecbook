import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchTeachers, hardReset } from "./api";
import ConfirmModal from "./ConfirmModal";
import { useTheme } from "./ThemeProvider";

export default function Teachers() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [toast, setToast] = useState({ type: "", msg: "" });

  const { t, mode, toggle } = useTheme();

  useEffect(() => {
    fetchTeachers().then(setRows);
  }, []);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return rows;

    return rows.filter((r) => {
      const name = (r.full_name || "").toLowerCase();
      const dept = (r.department || "").toLowerCase();
      const emp = (r.employee_id || "").toLowerCase();
      return name.includes(s) || dept.includes(s) || emp.includes(s);
    });
  }, [rows, q]);

  async function doHardReset() {
    setResetLoading(true);
    setToast({ type: "", msg: "" });

    try {
      const res = await hardReset();

      const refreshed = await fetchTeachers();
      setRows(refreshed);
      setQ("");

      setConfirmOpen(false);
      setToast({
        type: "success",
        msg: res?.message || "Reset complete: teachers + faces cleared.",
      });
    } catch (e) {
      setToast({ type: "error", msg: e.message || "Reset failed." });
    } finally {
      setResetLoading(false);
    }
  }

  const cardShadow = mode === "light" ? "0 8px 24px rgba(0,0,0,0.08)" : "none";
  const inputBg = mode === "light" ? "#FFFFFF" : "#0B1220";
  const rowBorder = mode === "light" ? "#F3F4F6" : "rgba(255,255,255,0.08)";

  const toastBg =
    toast.type === "success"
      ? mode === "light"
        ? "#ECFDF3"
        : "rgba(34,197,94,0.12)"
      : mode === "light"
      ? "#FEF2F2"
      : "rgba(248,113,113,0.12)";

  const toastText =
    toast.type === "success"
      ? mode === "light"
        ? "#166534"
        : "#86EFAC"
      : mode === "light"
      ? "#991B1B"
      : "#FCA5A5";

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
        <h2 style={{ margin: 0 }}>Teacher List</h2>

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

          <Link
            to="/home"
            style={{ color: "white", fontWeight: 700, textDecoration: "none" }}
          >
            Back
          </Link>
        </div>
      </header>

      <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
        {/* Search + Actions */}
        <div
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 14,
            boxShadow: cardShadow,
            border: `1px solid ${t.border}`,
            marginBottom: 16,
          }}
        >
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {/* Search Input */}
            <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
              <span
                style={{
                  position: "absolute",
                  left: 14,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: mode === "light" ? "#9CA3AF" : t.muted,
                  fontSize: 18,
                  userSelect: "none",
                }}
                aria-hidden="true"
              >
                {"\u{1F50D}"}
              </span>

              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by name, department, or employee ID..."
                style={{
                  width: "100%",
                  padding: "12px 14px 12px 44px",
                  borderRadius: 14,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  fontWeight: 700,
                  background: inputBg,
                  color: t.text,
                }}
              />
            </div>

            {/* Reset Button */}
            <button
              onClick={() => setConfirmOpen(true)}
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                border: "none",
                background: mode === "light" ? "#DC2626" : t.danger,
                color: "white",
                fontWeight: 900,
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
              title="Deletes all teachers, all uploaded faces, and the trained model"
            >
              Reset List
            </button>
          </div>

          <div style={{ marginTop: 10, color: t.muted, fontWeight: 700 }}>
            Showing <b style={{ color: t.text }}>{filtered.length}</b> of{" "}
            <b style={{ color: t.text }}>{rows.length}</b>
          </div>

          {/* Toast */}
          {toast.msg && (
            <div
              style={{
                marginTop: 12,
                padding: 12,
                borderRadius: 12,
                background: toastBg,
                border: `1px solid ${t.border}`,
              }}
            >
              <b style={{ color: toastText }}>
                {toast.type === "success" ? "Success: " : "Error: "}
              </b>
              <span style={{ color: t.text }}>{toast.msg}</span>
            </div>
          )}
        </div>

        {/* Table */}
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
                {["ID", "Name", "Department", "Employee ID", "Enrolled", "Actions"].map(
                  (h) => (
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
                  )
                )}
              </tr>
            </thead>

            <tbody>
              {filtered.map((r) => (
                <tr key={r.id}>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.id}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.full_name}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.department}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.employee_id}
                  </td>
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    {r.created_at}
                  </td>

                  {/* NEW: Actions */}
                  <td style={{ padding: 10, borderBottom: `1px solid ${rowBorder}` }}>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                      <Link
                        to={`/teachers/${r.id}/dtr`}
                        style={{
                          display: "inline-block",
                          padding: "8px 12px",
                          borderRadius: 10,
                          background: t.primary,
                          color: t.primaryText,
                          fontWeight: 900,
                          textDecoration: "none",
                        }}
                        title="View Daily Time Record"
                      >
                        {"\u{1F5D3} DTR"}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ padding: 14, color: t.muted }}>
                    No teachers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        open={confirmOpen}
        title="Reset teachers & faces?"
        message="This will permanently delete ALL teachers, ALL uploaded face images, and the trained model. This action cannot be undone."
        confirmText="Yes, reset everything"
        cancelText="Cancel"
        danger
        loading={resetLoading}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={doHardReset}
      />
    </div>
  );
}
