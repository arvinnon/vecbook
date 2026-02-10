export default function ConfirmModal({
  open,
  title = "Confirm",
  message = "Are you sure?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  danger = false,
  loading = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "grid",
        placeItems: "center",
        padding: 16,
        zIndex: 60,
      }}
      onClick={onCancel} // click outside closes
    >
      <div
        style={{
          width: "min(520px, 92vw)",
          background: "white",
          color: "#111827",
          borderRadius: 22,
          padding: 20,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
        onClick={(e) => e.stopPropagation()} // prevent outside click
      >
        <div style={{ fontSize: 18, fontWeight: 900 }}>{title}</div>
        <div style={{ marginTop: 10, color: "#6B7280", fontWeight: 700 }}>
          {message}
        </div>

        <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 12,
              border: "1px solid #E5E7EB",
              background: "white",
              fontWeight: 900,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {cancelText}
          </button>

          <button
            onClick={onConfirm}
            disabled={loading}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 12,
              border: "none",
              background: danger ? "#DC2626" : "#1A73E8",
              color: "white",
              fontWeight: 900,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.8 : 1,
            }}
          >
            {loading ? "Working..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
