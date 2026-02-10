import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "./assets/vecbook-logo.svg";
import { useTheme } from "./ThemeProvider";

export default function Splash() {
  const navigate = useNavigate();
  const { t } = useTheme();

  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    // start fade near the end
    const fadeTimer = setTimeout(() => setFadeOut(true), 4550); // start fade at 4.55s

    // navigate after 5s
    const navTimer = setTimeout(() => navigate("/home", { replace: true }), 5000);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(navTimer);
    };
  }, [navigate]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: t.bg,
        color: t.text,
        display: "grid",
        placeItems: "center",
        padding: 24,
        transition: "opacity 450ms ease, transform 450ms ease",
        opacity: fadeOut ? 0 : 1,
        transform: fadeOut ? "scale(0.98)" : "scale(1)",
      }}
    >
      <div style={{ textAlign: "center", width: "min(520px, 92vw)" }}>
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: 26,
            background: t.header,
            display: "grid",
            placeItems: "center",
            margin: "0 auto",
            boxShadow: t.shadow,
          }}
        >
          <img
            src={logo}
            alt="Vecbook"
            style={{
              width: 58,
              height: 58,
              filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.18))",
            }}
          />
        </div>

        <div
          style={{
            marginTop: 16,
            fontSize: 28,
            fontWeight: 900,
            letterSpacing: 0.5,
          }}
        >
          VECBOOK
        </div>

        <div style={{ marginTop: 6, color: t.muted, fontWeight: 700 }}>
          Facial Recognition Attendance System
        </div>

        {/* Loading bar */}
        <div
          style={{
            marginTop: 22,
            height: 10,
            width: "100%",
            borderRadius: 999,
            border: `1px solid ${t.border}`,
            background: t.card,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: "40%",
              background: t.primary,
              borderRadius: 999,
              animation: "vecbook-splash 1.2s ease-in-out infinite",
            }}
          />
        </div>

        <div style={{ marginTop: 10, color: t.muted, fontWeight: 700, fontSize: 13 }}>
          Loading...
        </div>
      </div>

      <style>{`
        @keyframes vecbook-splash {
          0%   { transform: translateX(-20%); width: 35%; opacity: 0.65; }
          50%  { transform: translateX(120%); width: 55%; opacity: 1; }
          100% { transform: translateX(-20%); width: 35%; opacity: 0.65; }
        }
      `}</style>
    </div>
  );
}
