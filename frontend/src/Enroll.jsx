import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { enrollWithFaces } from "./api";
import TrainingStatus from "./TrainingStatus";
import { useTheme } from "./ThemeProvider";

export default function Enroll() {
  const navigate = useNavigate();
  const { t, mode, toggle } = useTheme();

  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [files, setFiles] = useState([]);

  const [status, setStatus] = useState({ type: "", msg: "" });
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setStatus({ type: "", msg: "" });

    if (!files || files.length === 0) {
      setStatus({
        type: "error",
        msg: "Please upload at least 1 face image before enrolling.",
      });
      return;
    }

    setLoading(true);

    try {
      const res = await enrollWithFaces({
        full_name: fullName,
        department,
        employee_id: employeeId,
        files,
      });

      setStatus({
        type: "success",
        msg: `Enrolled: ${res.full_name} (ID ${res.id}). Saved ${res.saved} image(s). Auto-training started.`,
      });

      setFullName("");
      setDepartment("");
      setEmployeeId("");
      setFiles([]);

      setTimeout(() => navigate("/teachers"), 700);
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    } finally {
      setLoading(false);
    }
  }

  const cardShadow = t.shadow;
  const inputBg = t.inputBg;

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
        <h2 style={{ margin: 0 }}>Register Teacher</h2>

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
            {mode === "light" ? "🌙 Dark" : "☀️ Light"}
          </button>

          <Link
            to="/home"
            style={{ color: "white", fontWeight: 700, textDecoration: "none" }}
          >
            Back
          </Link>
        </div>
      </header>

      <div style={{ padding: 24, maxWidth: 650, margin: "0 auto" }}>
        <div
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 18,
            boxShadow: cardShadow,
            border: `1px solid ${t.border}`,
          }}
        >
          <div style={{ marginBottom: 14 }}>
            <TrainingStatus compact />
          </div>

          <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Full Name</div>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g., Juan Dela Cruz"
                style={{
                  width: "100%",
                  padding: 12,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  background: inputBg,
                  color: t.inputText,
                  fontWeight: 700,
                }}
              />
            </label>

            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Department</div>
              <input
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g., Math"
                style={{
                  width: "100%",
                  padding: 12,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  background: inputBg,
                  color: t.inputText,
                  fontWeight: 700,
                }}
              />
            </label>

            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Employee ID</div>
              <input
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                placeholder="e.g., EMP001"
                style={{
                  width: "100%",
                  padding: 12,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  background: inputBg,
                  color: t.inputText,
                  fontWeight: 700,
                }}
              />
            </label>

           
            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>
                Face Images{" "}
                <span style={{ color: t.danger, fontWeight: 900 }}>*required</span>
              </div>

              <input
                type="file"
                accept="image/png,image/jpeg"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                style={{
                  padding: 10,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  background: inputBg,
                  color: t.inputText,
                  width: "100%",
                }}
              />

              <div style={{ marginTop: 8, color: t.muted, fontSize: 13, fontWeight: 600 }}>
                Recommended: <b style={{ color: t.text }}>10–20</b> clear front-facing
                images (good lighting).
                {files.length > 0 && (
                  <>
                    <br />
                    Selected: <b style={{ color: t.text }}>{files.length}</b> file(s)
                  </>
                )}
              </div>
            </label>

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: 12,
                borderRadius: 12,
                background: t.primary,
                color: t.primaryText,
                border: "none",
                fontWeight: 900,
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.9 : 1,
              }}
            >
              {loading ? "Enrolling + Training..." : "Enroll Teacher"}
            </button>

            {status.msg && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  background:
                    status.type === "success" ? t.successBg : t.errorBg,
                  border: `1px solid ${t.border}`,
                }}
              >
                <b
                  style={{
                    color:
                      status.type === "success" ? t.successText : t.errorText,
                  }}
                >
                  {status.type === "success" ? "Success: " : "Error: "}
                </b>
                <span style={{ color: t.text }}>{status.msg}</span>
              </div>
            )}
          </form>

        </div>
      </div>
    </div>
  );
}
