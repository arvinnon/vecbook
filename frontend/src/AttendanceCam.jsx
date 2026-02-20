import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRecognitionConfig, recognizeFrame } from "./api";

const RECOGNITION_INTERVAL_MS = 30_000;
const RECOGNITION_INTERVAL_SECONDS = RECOGNITION_INTERVAL_MS / 1000;
const DEFAULT_WORKING_HOURS = {
  am_start: "05:00:00",
  am_end: "12:00:00",
  pm_start: "13:00:00",
  pm_end: "19:00:00",
};

function createSessionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `cam-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatTimeNow() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatTo12Hour(value) {
  if (!value) return "";
  const raw = String(value).trim();
  if (!raw) return "";
  if (/[AP]M/i.test(raw)) return raw;

  const m = raw.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return raw;

  let hh = Number(m[1]);
  const mm = m[2];
  const ss = m[3] || "00";
  const suffix = hh >= 12 ? "PM" : "AM";
  hh %= 12;
  if (hh === 0) hh = 12;
  return `${String(hh).padStart(2, "0")}:${mm}:${ss} ${suffix}`;
}

function parseHmsToSeconds(value) {
  if (!value) return null;
  const m = String(value).trim().match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return null;
  const hh = Number(m[1]);
  const mm = Number(m[2]);
  const ss = Number(m[3] || "0");
  if (
    Number.isNaN(hh) ||
    Number.isNaN(mm) ||
    Number.isNaN(ss) ||
    hh < 0 ||
    hh > 23 ||
    mm < 0 ||
    mm > 59 ||
    ss < 0 ||
    ss > 59
  ) {
    return null;
  }
  return hh * 3600 + mm * 60 + ss;
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
  const countdownRef = useRef(null);
  const nextScanAtRef = useRef(null);
  const noMatchCountRef = useRef(0);
  const sessionIdRef = useRef(createSessionId());

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Camera off");
  const [verifying, setVerifying] = useState(false);
  const [secondsToNextScan, setSecondsToNextScan] = useState(null);
  const [workingHours, setWorkingHours] = useState(DEFAULT_WORKING_HOURS);
  const [clockTick, setClockTick] = useState(() => Date.now());

  const [success, setSuccess] = useState(null);

  const amStartSeconds = parseHmsToSeconds(workingHours.am_start) ?? parseHmsToSeconds(DEFAULT_WORKING_HOURS.am_start);
  const amEndSeconds = parseHmsToSeconds(workingHours.am_end) ?? parseHmsToSeconds(DEFAULT_WORKING_HOURS.am_end);
  const pmStartSeconds = parseHmsToSeconds(workingHours.pm_start) ?? parseHmsToSeconds(DEFAULT_WORKING_HOURS.pm_start);
  const pmEndSeconds = parseHmsToSeconds(workingHours.pm_end) ?? parseHmsToSeconds(DEFAULT_WORKING_HOURS.pm_end);
  const now = new Date(clockTick);
  const nowSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const inAmWindow = amStartSeconds != null && amEndSeconds != null && nowSeconds >= amStartSeconds && nowSeconds < amEndSeconds;
  const inPmWindow = pmStartSeconds != null && pmEndSeconds != null && nowSeconds >= pmStartSeconds && nowSeconds < pmEndSeconds;
  const outsideWorkingHours = !inAmWindow && !inPmWindow;
  const workingHoursLabel = `${formatTo12Hour(workingHours.am_start)}-${formatTo12Hour(workingHours.am_end)} and ${formatTo12Hour(workingHours.pm_start)}-${formatTo12Hour(workingHours.pm_end)}`;

  function startCountdown() {
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      const nextScanAt = nextScanAtRef.current;
      if (!nextScanAt) {
        setSecondsToNextScan(null);
        return;
      }
      const remainingMs = nextScanAt - Date.now();
      const remainingSeconds = Math.ceil(remainingMs / 1000);
      setSecondsToNextScan(Math.max(1, remainingSeconds));
    }, 250);
  }

  function stopCountdown() {
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = null;
    nextScanAtRef.current = null;
    setSecondsToNextScan(null);
  }

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
    setStatus("Scanning every 30 seconds...");
    nextScanAtRef.current = Date.now() + RECOGNITION_INTERVAL_MS;
    setSecondsToNextScan(RECOGNITION_INTERVAL_SECONDS);
    startCountdown();
    noMatchCountRef.current = 0;
    sendFrameOnce();
    timerRef.current = setInterval(sendFrameOnce, RECOGNITION_INTERVAL_MS);
  }

  function stopRecognitionLoop() {
    setRunning(false);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    stopCountdown();
    if (!success) setStatus("Recognition stopped");
  }

  const closeModalAndResume = () => {
    stopRecognitionLoop();
    setSuccess(null);
    setStatus("Ready. Click Start Recognition.");
    setVerifying(false);
    noMatchCountRef.current = 0;
  };

  async function sendFrameOnce() {
    if (verifying || success) return;
    nextScanAtRef.current = Date.now() + RECOGNITION_INTERVAL_MS;
    setSecondsToNextScan(RECOGNITION_INTERVAL_SECONDS);

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

      const res = await recognizeFrame(blob, sessionIdRef.current);

      if (res?.reason === "unknown_face") {
        noMatchCountRef.current = 0;
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
        if (res?.reason === "pending_confirmation") {
          noMatchCountRef.current = 0;
          const n = res?.count || 1;
          const need = res?.needed || 2;
          setStatus(`Hold still... (${n}/${need})`);
          return;
        }
        if (res?.reason === "model_missing") {
          noMatchCountRef.current = 0;
          setSuccess({
            type: "no_match",
            title: "Model not ready",
            message: "Face model is missing. Please wait for training to finish, then try again.",
          });
          stopRecognitionLoop();
          setStatus("Model missing. Run training first.");
          return;
        }
        if (res?.reason === "low_confidence") {
          noMatchCountRef.current += 1;
          if (noMatchCountRef.current >= 3) {
            setSuccess({
              type: "no_match",
              title: "Low confidence match",
              message: "Face match is too weak. Please try again or enroll first.",
            });
            stopRecognitionLoop();
            setStatus("Low confidence match");
            return;
          }
          setStatus(`Low confidence. Retrying (${noMatchCountRef.current}/3)`);
          return;
        }
        noMatchCountRef.current += 1;
        if (noMatchCountRef.current >= 3) {
          setSuccess({
            type: "no_match",
            title: "No match found",
            message: "Face not recognized. Please try again or enroll first.",
          });
          stopRecognitionLoop();
          setStatus("No match");
          return;
        }
        const reasonSuffix = res?.reason ? ` (${res.reason})` : "";
        setStatus(`No match${reasonSuffix}. Retrying (${noMatchCountRef.current}/3)`);
        return;
      }
      noMatchCountRef.current = 0;
      const fullName = res?.full_name || `Teacher ID ${res.teacher_id}`;
      const department = res?.department || "-";

      const isLoggedPunch = res.logged === true;
      const eventTimeRaw = isLoggedPunch
        ? res.time_in || formatTimeNow()
        : res.time || formatTimeNow();
      const eventTime = formatTo12Hour(eventTimeRaw);
      const eventTimeLabel = isLoggedPunch ? "Time In" : "Scan Time";
      const alreadyLogged =
        res.reason === "day_complete" || res.reason === "already_logged";
      const statusText =
        isLoggedPunch
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
        event_time: eventTime,
        event_time_label: eventTimeLabel,
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

  useEffect(() => {
    let mounted = true;
    fetchRecognitionConfig()
      .then((cfg) => {
        if (!mounted || !cfg) return;
        setWorkingHours({
          am_start: cfg.am_start || DEFAULT_WORKING_HOURS.am_start,
          am_end: cfg.am_end || DEFAULT_WORKING_HOURS.am_end,
          pm_start: cfg.pm_start || DEFAULT_WORKING_HOURS.pm_start,
          pm_end: cfg.pm_end || DEFAULT_WORKING_HOURS.pm_end,
        });
      })
      .catch(() => {
        // keep defaults when config is unavailable
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setClockTick(Date.now()), 1000);
    return () => clearInterval(timer);
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
                padding: 12,
                borderRadius: 12,
                border: outsideWorkingHours ? "1px solid #FCA5A5" : "1px solid #BFDBFE",
                background: outsideWorkingHours ? "#FEF2F2" : "#EFF6FF",
                color: outsideWorkingHours ? "#991B1B" : "#1E40AF",
                fontWeight: 700,
              }}
            >
              <div style={{ fontWeight: 900 }}>
                {outsideWorkingHours ? "Outside working hours" : "Within working hours"}
              </div>
              <div style={{ marginTop: 4 }}>
                Schedule: {workingHoursLabel}
              </div>
              {outsideWorkingHours && (
                <div style={{ marginTop: 4 }}>
                  Scans beyond working hours are not logged as DTR time-in.
                </div>
              )}
            </div>

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
              {running && !verifying && typeof secondsToNextScan === "number"
                ? ` (next scan in ${secondsToNextScan}s)`
                : ""}
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

      {success && success.type === "no_match" && (
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
                  background: "#FEE2E2",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <div style={{ fontSize: 30, color: "#B91C1C" }}>{"\u00D7"}</div>
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
              Try Again
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
              <span style={{ fontWeight: 800 }}>
                {success.event_time_label || "Time In"}:
              </span>
              <span>{success.event_time}</span>
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
