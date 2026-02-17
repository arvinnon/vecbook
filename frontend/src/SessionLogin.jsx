import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearSession, createSession, fetchSessionMe, hasSession } from "./api";
import { useTheme } from "./ThemeProvider";

export default function SessionLogin() {
  const navigate = useNavigate();
  const { t, mode, toggle } = useTheme();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: "", msg: "" });

  async function onSubmit(e) {
    e.preventDefault();
    setStatus({ type: "", msg: "" });

    if (!username.trim() || !password.trim()) {
      setStatus({ type: "error", msg: "Username and password are required." });
      return;
    }

    setLoading(true);
    try {
      const session = await createSession({
        username: username.trim(),
        password: password.trim(),
      });
      setStatus({
        type: "success",
        msg: `Authenticated as ${session.username}. Session expires in ${session.expires_in}s.`,
      });
      setTimeout(() => navigate("/home", { replace: true }), 300);
    } catch (err) {
      setStatus({ type: "error", msg: err.message || "Authentication failed." });
    } finally {
      setLoading(false);
    }
  }

  async function checkSession() {
    setStatus({ type: "", msg: "" });
    try {
      const data = await fetchSessionMe();
      setStatus({
        type: "success",
        msg: `Session valid for vecbook ${data.username}.`,
      });
    } catch (err) {
      setStatus({ type: "error", msg: err.message || "Login is not valid." });
    }
  }

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
        <h2 style={{ margin: 0 }}>VECBOOK</h2>
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
            {mode === "light" ? "Dark" : "Light"}
          </button>
         
        </div>
      </header>

      <div style={{ padding: 24, maxWidth: 540, margin: "0 auto" }}>
        <div
          style={{
            background: t.card,
            borderRadius: 18,
            padding: 18,
            boxShadow: t.shadow,
            border: `1px solid ${t.border}`,
          }}
        >
          <div style={{ color: t.muted, fontWeight: 700, marginBottom: 14 }}>
            VECBOOK ADMIN
          </div>

          <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Username</div>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g., admin"
                style={{
                  width: "100%",
                  padding: 12,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  background: t.inputBg,
                  color: t.inputText,
                  fontWeight: 700,
                }}
              />
            </label>

            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Password</div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter admin password"
                style={{
                  width: "100%",
                  padding: 12,
                  borderRadius: 12,
                  border: `1px solid ${t.border}`,
                  outline: "none",
                  background: t.inputBg,
                  color: t.inputText,
                  fontWeight: 700,
                }}
              />
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
              }}
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

        

          {status.msg && (
            <div
              style={{
                marginTop: 14,
                padding: 12,
                borderRadius: 12,
                background: status.type === "success" ? t.successBg : t.errorBg,
                border: `1px solid ${t.border}`,
              }}
            >
              <b style={{ color: status.type === "success" ? t.successText : t.errorText }}>
                {status.type === "success" ? "Success: " : "Error: "}
              </b>
              <span style={{ color: t.text }}>{status.msg}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
