import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { recognizeFrame, fetchTeacherById } from "./api";

function formatTimeNow() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
function confidenceLabel(conf, threshold = 70) {
  if (conf == null) return "";
  if (conf <= threshold * 0.55) return "Strong match";
  if (conf <= threshold * 0.85) return "Good match";
  if (conf <= threshold) return "Weak match";
  return "Not a match";
}

export default function AttendanceCam() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const timerRef = useRef(null);

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Camera off");
  const [verifying, setVerifying] = useState(false);

  const [success, setSuccess] = useState(null);

  async function startCamera() {
    setStatus("Starting camera...");
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

    setStatus("Camera ready. Click Start Recognition.");
  }

  function stopCamera() {
    const v = videoRef.current;
    if (v?.srcObject) {
      v.srcObject.getTracks().forEach((t) => t.stop());
      v.srcObject = null;
    }
  }

  function startRecognitionLoop() {
    // prevent duplicate intervals
    if (timerRef.current) return;

    setRunning(true);
    setStatus("Scanning...");
    timerRef.current = setInterval(sendFrameOnce, 1000); 
  }

  function stopRecognitionLoop() {
    setRunning(false);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    if (!success) setStatus("Recognition stopped");
  }

  const closeModalAndResume = () => {
    setSuccess(null);
    setStatus("Scanning...");
    setVerifying(false);
    setTimeout(() => startRecognitionLoop(), 250);
  };

  async function sendFrameOnce() {
    if (verifying || success) return;

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
      canvas.toBlob(resolve, "image/jpeg", 0.85)
    );
    if (!blob) return;

    try {
      setVerifying(true);
      setStatus("Verifying identity...");

      const res = await recognizeFrame(blob);

      if (res?.reason === "unknown_face") {
        setSuccess({
          type: "unknown",
          title: "Face recognized",
          message: "Face recognized but not enrolled",
        });
        stopRecognitionLoop();
        setStatus("Unknown face detected");
        return;
      }
      if (!res?.verified) {
        setStatus("No match / no face detected");
        return;
      }
      const t = await fetchTeacherById(res.teacher_id);
      const fullName = t?.found ? t.full_name : `Teacher ID ${res.teacher_id}`;
      const department = t?.found ? t.department : "-";

      const timeIn = res.time_in || formatTimeNow();
      const alreadyLogged =
        res.reason === "day_complete" || res.reason === "already_logged";
      const statusText =
        res.logged === true
          ? res.status || "Logged"
          : alreadyLogged
          ? "Already Logged Today"
          : res.reason === "lunch_break"
          ? "Lunch break (12:00-13:00)"
          : res.reason === "out_of_shift"
          ? "Outside shift hours"
          : "Verified";

      setSuccess({
        type: "success",
        full_name: fullName,
        department,
        time_in: timeIn,
        status: statusText,
        confidence: res.confidence,
      });

      stopRecognitionLoop();
      setStatus(
        `Matched Teacher ID ${res.teacher_id} | conf=${
          typeof res.confidence === "number"
            ? res.confidence.toFixed(2)
            : res.confidence
        }`
      );
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  }

  useEffect(() => {
    startCamera().catch((e) => setStatus(`Camera error: ${e.message}`));
    return () => {
      stopRecognitionLoop();
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ background: "#F5F7FA", minHeight: "100vh" }}>
      <header className="header">
        <div className="headerRow">
          <h2 className="headerTitle">Start Attendance</h2>
          <Link
            to="/home"
            style={{ color: "white", fontWeight: 700, textDecoration: "none" }}
          >
            Back
          </Link>
        </div>
      </header>

      <div className="container" style={{ display: "grid", gap: 16 }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ fontWeight: 800 }}>Live Camera</div>

            <div
              style={{
                width: "100%",
                borderRadius: 16,
                overflow: "hidden",
                background: "#111827",
                position: "relative",
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

              {verifying && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "grid",
                    placeItems: "center",
                    background: "rgba(0,0,0,0.45)",
                    color: "white",
                    fontWeight: 900,
                  }}
                >
                  <div
                    style={{
                      background: "rgba(0,0,0,0.6)",
                      padding: "10px 14px",
                      borderRadius: 14,
                      border: "1px solid rgba(255,255,255,0.15)",
                      backdropFilter: "blur(10px)",
                    }}
                  >
                    Verifying identity...{" "}
                    <span style={{ color: "#60A5FA" }}>...</span>
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                className="buttonPrimary"
                onClick={startRecognitionLoop}
                disabled={running || verifying}
              >
                Start Recognition
              </button>

              <button
                onClick={stopRecognitionLoop}
                disabled={!running}
                style={{
                  padding: 12,
                  borderRadius: 12,
                  border: "1px solid #E5E7EB",
                  background: "white",
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                Stop
              </button>
            </div>

            <div
              style={{ padding: 12, borderRadius: 12, background: "#EEF2FF" }}
            >
              <b>Status:</b> {status}
            </div>
          </div>

          <canvas ref={canvasRef} style={{ display: "none" }} />
        </div>
      </div>

      {success && success.type === "unknown" && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "grid",
            placeItems: "center",
            padding: 16,
            zIndex: 50,
          }}
        >
          <div
            style={{
              width: "min(520px, 92vw)",
              background: "white",
              color: "#111827",
              borderRadius: 22,
              padding: 22,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
              textAlign: "center",
            }}
          >
            <div style={{ display: "grid", placeItems: "center" }}>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "#FEF3C7",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <div style={{ fontSize: 30, color: "#B45309" }}>!</div>
              </div>
            </div>

            <div style={{ fontSize: 22, fontWeight: 900, marginTop: 12 }}>
              {success.title}
            </div>

            <div style={{ marginTop: 10, color: "#6B7280", fontWeight: 700 }}>
              {success.message}
            </div>

            <button
              onClick={closeModalAndResume}
              style={{
                marginTop: 16,
                width: "100%",
                padding: 14,
                borderRadius: 14,
                background: "#1A73E8",
                color: "white",
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {success && success.type === "success" && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "grid",
            placeItems: "center",
            padding: 16,
            zIndex: 50,
          }}
        >
          <div
            style={{
              width: "min(520px, 92vw)",
              background: "white",
              color: "#111827",
              borderRadius: 22,
              padding: 22,
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
              textAlign: "center",
            }}
          >
            <div style={{ display: "grid", placeItems: "center" }}>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "#DCFCE7",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <div style={{ fontSize: 30, color: "#16A34A" }}>{"\u2713"}</div>
              </div>
            </div>

            <div style={{ fontSize: 22, fontWeight: 900, marginTop: 12 }}>
              Welcome Back!
            </div>

            <div
              style={{
                background: "#F3F4F6",
                borderRadius: 16,
                padding: 16,
                marginTop: 14,
              }}
            >
              <div style={{ fontSize: 12, color: "#6B7280", fontWeight: 800 }}>
                Teacher Name
              </div>
              <div style={{ fontSize: 18, fontWeight: 900, marginTop: 4 }}>
                {success.full_name}
              </div>

              <div style={{ height: 12 }} />

              <div style={{ fontSize: 12, color: "#6B7280", fontWeight: 800 }}>
                Department
              </div>
              <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4 }}>
                {success.department}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: 10,
                marginTop: 14,
                color: "#4B5563",
              }}
            >
              <span>{"\u{1F552}"}</span>
              <span style={{ fontWeight: 800 }}>Time In:</span>
              <span>{success.time_in}</span>
            </div>

            {typeof success.confidence === "number" && (
              <div style={{ marginTop: 6, color: "#6B7280", fontWeight: 800 }}>
                Confidence: {success.confidence.toFixed(2)} -{" "}
                {confidenceLabel(success.confidence)}
              </div>
            )}

            <div style={{ marginTop: 10, color: "#1A73E8", fontWeight: 900 }}>
              {success.status}
            </div>

            <button
              onClick={closeModalAndResume}
              style={{
                marginTop: 16,
                width: "100%",
                padding: 14,
                borderRadius: 14,
                background: "#1A73E8",
                color: "white",
                border: "none",
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
