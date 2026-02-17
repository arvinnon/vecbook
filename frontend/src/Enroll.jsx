import { useEffect, useRef, useState } from "react";
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
  const [captures, setCaptures] = useState([]);
  const [cameraOn, setCameraOn] = useState(false);
  const [autoCapturing, setAutoCapturing] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const autoRef = useRef(null);
  const captureCountRef = useRef(0);

  const [status, setStatus] = useState({ type: "", msg: "" });
  const [loading, setLoading] = useState(false);

  const CAPTURE_TARGET = 12;
  const MIN_CAPTURES = 8;

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
    } catch (e) {
      setStatus({ type: "error", msg: `Camera error: ${e.message}` });
    }
  }

  function stopCamera() {
    stopAutoCapture();
    const v = videoRef.current;
    if (v?.srcObject) {
      v.srcObject.getTracks().forEach((t) => t.stop());
      v.srcObject = null;
    }
    setCameraOn(false);
  }

  async function captureFrameOnce() {
    if (captureCountRef.current >= CAPTURE_TARGET) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;

    const targetW = 640;
    const targetH = Math.round((h / w) * targetW);

    canvas.width = targetW;
    canvas.height = targetH;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, targetW, targetH);

    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9)
    );
    if (!blob) return;

    setCaptures((prev) => [...prev, blob]);
  }

  async function startAutoCapture() {
    if (autoCapturing || !cameraOn) return;
    setAutoCapturing(true);
    autoRef.current = setInterval(async () => {
      if (captureCountRef.current >= CAPTURE_TARGET) {
        stopAutoCapture();
        return;
      }
      await captureFrameOnce();
    }, 300);
  }

  function stopAutoCapture() {
    if (autoRef.current) {
      clearInterval(autoRef.current);
      autoRef.current = null;
    }
    setAutoCapturing(false);
  }

  useEffect(() => {
    captureCountRef.current = captures.length;
    if (autoCapturing && captures.length >= CAPTURE_TARGET) {
      stopAutoCapture();
    }
  }, [captures, autoCapturing]);

  useEffect(() => {
    return () => {
      stopAutoCapture();
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setStatus({ type: "", msg: "" });

    if (!fullName.trim() || !department.trim() || !employeeId.trim()) {
      setStatus({
        type: "error",
        msg: "Please fill out Full Name, Department, and Employee ID.",
      });
      return;
    }

    if (!captures || captures.length < MIN_CAPTURES) {
      setStatus({
        type: "error",
        msg: `Please capture at least ${MIN_CAPTURES} face images before enrolling.`,
      });
      return;
    }

    setLoading(true);

    try {
      const files = captures.map(
        (blob, i) => new File([blob], `capture_${i + 1}.jpg`, { type: blob.type || "image/jpeg" })
      );
      const res = await enrollWithFaces({
        full_name: fullName,
        department,
        employee_id: employeeId,
        files,
      });
      setStatus({
        type: "success",
        msg: `Enrolled: ${res.full_name} (ID ${res.id}). Saved ${res.saved} image(s). ${res.training_message || "Training started."}`,
      });

      setFullName("");
      setDepartment("");
      setEmployeeId("");
      setCaptures([]);

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

            <div style={{ fontWeight: 800, marginBottom: 6 }}>
              Live Face Capture{" "}
              <span style={{ color: t.danger, fontWeight: 900 }}>*required</span>
            </div>

            <div
              style={{
                width: "100%",
                borderRadius: 16,
                overflow: "hidden",
                background: "#111827",
                position: "relative",
                border: `1px solid ${t.border}`,
              }}
            >
              <video
                ref={videoRef}
                style={{ width: "100%", display: "block" }}
                playsInline
              />
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "grid",
                  placeItems: "center",
                  pointerEvents: "none",
                }}
              >
                <div
                  style={{
                    width: "55%",
                    aspectRatio: "1 / 1",
                    borderRadius: "50%",
                    border: "3px solid #60A5FA",
                    boxShadow: "0 0 0 9999px rgba(0,0,0,0.35)",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={startCamera}
                disabled={cameraOn}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #E5E7EB",
                  background: "white",
                  fontWeight: 900,
                  cursor: cameraOn ? "not-allowed" : "pointer",
                }}
              >
                Start Camera
              </button>
              <button
                type="button"
                onClick={stopCamera}
                disabled={!cameraOn}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #E5E7EB",
                  background: "white",
                  fontWeight: 900,
                  cursor: !cameraOn ? "not-allowed" : "pointer",
                }}
              >
                Stop
              </button>
              <button
                type="button"
                onClick={captureFrameOnce}
                disabled={!cameraOn || autoCapturing || captures.length >= CAPTURE_TARGET}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: t.primary,
                  color: t.primaryText,
                  border: "none",
                  fontWeight: 900,
                  cursor: !cameraOn || autoCapturing || captures.length >= CAPTURE_TARGET ? "not-allowed" : "pointer",
                  opacity: !cameraOn || autoCapturing || captures.length >= CAPTURE_TARGET ? 0.8 : 1,
                }}
              >
                Capture
              </button>
              <button
                type="button"
                onClick={startAutoCapture}
                disabled={!cameraOn || autoCapturing}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: t.success,
                  color: t.successText,
                  border: "none",
                  fontWeight: 900,
                  cursor: !cameraOn || autoCapturing ? "not-allowed" : "pointer",
                  opacity: !cameraOn || autoCapturing ? 0.8 : 1,
                }}
              >
                Auto Capture ({CAPTURE_TARGET})
              </button>
              <button
                type="button"
                onClick={() => setCaptures([])}
                disabled={captures.length === 0}
                style={{
                  padding: "10px 12px",
                  borderRadius: 12,
                  border: "1px solid #E5E7EB",
                  background: "white",
                  fontWeight: 900,
                  cursor: captures.length === 0 ? "not-allowed" : "pointer",
                }}
              >
                Clear
              </button>
            </div>

            <div style={{ marginTop: 6, color: t.muted, fontSize: 13, fontWeight: 600 }}>
              Captured: <b style={{ color: t.text }}>{captures.length}</b> / {CAPTURE_TARGET}
              {captures.length < MIN_CAPTURES && (
                <>
                  {" "}
                  | Minimum required: <b style={{ color: t.text }}>{MIN_CAPTURES}</b>
                </>
              )}
            </div>

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
          <canvas ref={canvasRef} style={{ display: "none" }} />

        </div>
      </div>
    </div>
  );
}
