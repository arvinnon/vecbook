import { Link } from "react-router-dom";
import logo from "./assets/vecbook-logo.svg";
import { useTheme } from "./ThemeProvider";

function CardLink({ to, icon, title, desc, t }) {
  return (
    <Link
      to={to}
      className="card cardLink"
      style={{
        background: t.card,
        border: `1px solid ${t.border}`,
        boxShadow: t.shadow,
        color: t.text,
        textDecoration: "none",
      }}
    >
      <div
        className="iconBubble"
        style={{
          background: t.name === "light" ? "#EEF2FF" : "rgba(96,165,250,0.16)",
          border: `1px solid ${t.border}`,
          color: t.text,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontWeight: 800, fontSize: 16 }}>{title}</div>
        <div style={{ marginTop: 6, fontSize: 13, color: t.muted, fontWeight: 600 }}>
          {desc}
        </div>
      </div>
    </Link>
  );
}

function CardDisabled({ icon, title, desc, t }) {
  return (
    <div
      className="card cardLink"
      style={{
        opacity: 0.6,
        cursor: "not-allowed",
        background: t.card,
        border: `1px solid ${t.border}`,
        boxShadow: t.shadow,
        color: t.text,
      }}
    >
      <div
        className="iconBubble"
        style={{
          background: t.name === "light" ? "#EEF2FF" : "rgba(96,165,250,0.16)",
          border: `1px solid ${t.border}`,
          color: t.text,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontWeight: 800, fontSize: 16 }}>{title}</div>
        <div style={{ marginTop: 6, fontSize: 13, color: t.muted, fontWeight: 600 }}>
          {desc}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { t, mode, toggle } = useTheme();

  return (
    <div style={{ background: t.bg, minHeight: "100vh", color: t.text }}>
      <header
        style={{
          background: t.header,
          color: t.headerText,
          padding: 18,
          display: "flex",
          alignItems: "center",
          gap: 14,
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <img
            src={logo}
            alt="Vecbook Logo"
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "rgba(255,255,255,0.15)",
              padding: 4,
            }}
          />

          
          <div style={{ lineHeight: 1.1 }}>
            <h2 style={{ margin: 0, fontWeight: 900, letterSpacing: 0.4 }}>
              VECBOOK
            </h2>
            <div style={{ fontSize: 12, color: t.headerSub, fontWeight: 600 }}>
              Facial Recognition Attendance System
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
              whiteSpace: "nowrap",
            }}
            title="Toggle theme"
          >
            {mode === "light" ? "\u{1F319} Dark" : "\u2600\uFE0F Light"}
          </button>
          <Link
            to="/login"
            style={{
              color: "white",
              fontWeight: 800,
              textDecoration: "none",
              padding: "8px 10px",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.25)",
              background: "rgba(255,255,255,0.12)",
            }}
          >
            Session
          </Link>
        </div>
      </header>

      <div className="container">
        <div className="grid">
          <CardLink
            to="/enroll"
            icon={"\u2795"}
            title="Register Teacher"
            desc="Add a new teacher profile"
            t={t}
          />
          <CardLink
            to="/camera"
            icon={"\u{1F4F7}"}
            title="Start Attendance"
            desc="Webcam recognition"
            t={t}
          />
          <CardLink
            to="/teachers"
            icon={"\u{1F469}\u200D\u{1F3EB}"}
            title="Teacher List"
            desc="View registered teachers"
            t={t}
          />
          <CardLink
            to="/records"
            icon={"\u{1F4CB}"}
            title="Attendance Records"
            desc="Logs & daily summary"
            t={t}
          />
        </div>
      </div>
    </div>
  );
}
