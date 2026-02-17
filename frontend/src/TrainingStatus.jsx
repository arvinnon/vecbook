import { useEffect, useRef, useState } from "react";
import { fetchTrainStatus, runTraining } from "./api";

function pillStyle(bg, fg) {
  return {
    display: "inline-flex",
    gap: 8,
    alignItems: "center",
    padding: "8px 12px",
    borderRadius: 999,
    background: bg,
    color: fg,
    fontWeight: 900,
    fontSize: 13,
  };
}

function dot(color) {
  return {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: color,
    display: "inline-block",
  };
}

export default function TrainingStatus({ compact = false }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const timerRef = useRef(null);

  async function refresh() {
    try {
      setErr("");
      const s = await fetchTrainStatus();
      setData(s);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, 1500); // poll
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div style={pillStyle("#EEF2FF", "#1F2937")}>
        <span style={dot("#60A5FA")} />
        Checking training status...
      </div>
    );
  }

  if (err) {
    return (
      <div style={pillStyle("#FEF2F2", "#991B1B")}>
        <span style={dot("#EF4444")} />
        Training status unavailable
      </div>
    );
  }

  const state = data?.state || "idle";
  const message = data?.message || "";
  const queued = Boolean(data?.queued);

  let pill;
  if (state === "running") {
    pill = pillStyle("#FEF3C7", "#92400E");
  } else if (state === "success") {
    pill = pillStyle("#ECFDF3", "#166534");
  } else if (state === "failed") {
    pill = pillStyle("#FEF2F2", "#991B1B");
  } else {
    pill = pillStyle("#EEF2FF", "#1F2937");
  }

  const label =
    state === "running"
      ? "Training in progress..."
      : state === "success"
      ? "Model updated \u2705"
      : state === "failed"
      ? "Training failed \u274C"
      : "Training idle";
  const labelWithQueue = queued ? `${label} (queued)` : label;

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={pill}>
        <span
          style={dot(
            state === "running"
              ? "#F59E0B"
              : state === "success"
              ? "#22C55E"
              : state === "failed"
              ? "#EF4444"
              : "#60A5FA"
          )}
        />
        {labelWithQueue}
        {!compact && data?.started_at && (
          <span style={{ opacity: 0.85, fontWeight: 800 }}>
            Started: {data.started_at}
          </span>
        )}
      </div>

      {!compact && (
        <div style={{ color: "#6B7280", fontSize: 13 }}>
          {message}
          {data?.last_success ? (
            <>
              <br />
              Last success: <b>{data.last_success}</b>
            </>
          ) : null}
        </div>
      )}

      {!compact && (
        <button
          onClick={async () => {
            try {
              await runTraining();
              await refresh();
            } catch (e) {
              setErr(e.message);
            }
          }}
          style={{
            width: "fit-content",
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid #E5E7EB",
            background: "white",
            fontWeight: 900,
            cursor: "pointer",
          }}
        >
          Retrain now
        </button>
      )}
    </div>
  );
}
