import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearSession, createSession, fetchSessionMe, hasSession } from "./api";
import { useTheme } from "./ThemeProvider";

export default function SessionLogin() {
  const navigate = useNavigate();
  const { t, mode, toggle } = useTheme();
  const [deviceId, setDeviceId] = useState("frontend-console");
  const [deviceSecret, setDeviceSecret] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: "", msg: "" });

  async function onSubmit(e) {
    e.preventDefault();
    setStatus({ type: "", msg: "" });

    if (!deviceId.trim() || !deviceSecret.trim()) {
      setStatus({ type: "error", msg: "Device ID and Device Secret are required." });
      return;
    }

    setLoading(true);
    try {
      const session = await createSession({
        device_id: deviceId.trim(),
        device_secret: deviceSecret.trim(),
      });
      setStatus({
        type: "success",
        msg: `Authenticated. Session expires in ${session.expires_in}s.`,
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
        msg: `Session valid for ${data.device_id}.`,
      });
    } catch (err) {
      setStatus({ type: "error", msg: err.message || "Session is not valid." });
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
        <h2 style={{ margin: 0 }}>Session Login</h2>
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
          <Link to="/home" style={{ color: "white", fontWeight: 700, textDecoration: "none" }}>
            Home
          </Link>
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
            Authenticate this client to call protected write/admin endpoints.
          </div>

          <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
            <label>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Device ID</div>
              <input
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                placeholder="e.g., registrar-kiosk-1"
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
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Device Secret</div>
              <input
                type="password"
                value={deviceSecret}
                onChange={(e) => setDeviceSecret(e.target.value)}
                placeholder="Enter VECBOOK_DEVICE_SECRET"
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
              {loading ? "Signing in..." : "Create Session"}
            </button>
          </form>

          <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={checkSession}
              disabled={!hasSession()}
              style={{
                padding: "10px 12px",
                borderRadius: 12,
                border: `1px solid ${t.border}`,
                background: t.card,
                color: t.text,
                fontWeight: 800,
                cursor: hasSession() ? "pointer" : "not-allowed",
              }}
            >
              Check Current Session
            </button>

            <button
              type="button"
              onClick={() => {
                clearSession();
                setStatus({ type: "success", msg: "Session cleared." });
              }}
              disabled={!hasSession()}
              style={{
                padding: "10px 12px",
                borderRadius: 12,
                border: `1px solid ${t.border}`,
                background: t.card,
                color: t.text,
                fontWeight: 800,
                cursor: hasSession() ? "pointer" : "not-allowed",
              }}
            >
              Sign Out
            </button>
          </div>

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
