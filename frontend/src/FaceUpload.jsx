import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { uploadFaces, fetchTeacherById } from "./api";

export default function FaceUpload() {
  const { id } = useParams(); // teacher_id
  const teacherId = Number(id);

  const [teacher, setTeacher] = useState(null);
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState({ type: "", msg: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTeacherById(teacherId)
      .then(setTeacher)
      .catch(() => setTeacher({ found: false }));
  }, [teacherId]);

  async function onUpload(e) {
    e.preventDefault();
    setStatus({ type: "", msg: "" });

    if (!files || files.length < 3) {
      setStatus({
        type: "error",
        msg: "Please select at least 3 face images (JPG/PNG).",
      });
      return;
    }

    setLoading(true);
    try {
      const res = await uploadFaces(teacherId, files);
      setStatus({
        type: "success",
        msg: `Uploaded ${res.saved} image(s) successfully.`,
      });
      setFiles([]);
    } catch (err) {
      setStatus({ type: "error", msg: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ background: "#F5F7FA", minHeight: "100vh" }}>
      <header
        style={{
          background: "#1A73E8",
          color: "white",
          padding: 18,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <h2 style={{ margin: 0 }}>Upload Face Images</h2>
        <Link to="/" style={{ color: "white", fontWeight: 700 }}>
          Back
        </Link>
      </header>

      <div style={{ padding: 24, maxWidth: 700, margin: "0 auto" }}>
        <div
          style={{
            background: "white",
            borderRadius: 18,
            padding: 18,
            boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
          }}
        >
          {/* ✅ Teacher Info */}
          {teacher?.found ? (
            <>
              <div style={{ fontSize: 20, fontWeight: 900 }}>
                {teacher.full_name}
              </div>
              <div style={{ color: "#6B7280", marginBottom: 6 }}>
                Department: {teacher.department}
              </div>
              <div style={{ color: "#9CA3AF", marginBottom: 14 }}>
                Teacher ID: {teacher.id}
              </div>
            </>
          ) : (
            <div style={{ marginBottom: 14, fontWeight: 800 }}>
              Teacher ID: {teacherId}
            </div>
          )}

          <div style={{ color: "#6B7280", marginBottom: 16 }}>
            Upload clear face images (front-facing, good lighting).
            <br />
            Recommended: <b>10–20 images</b>.
          </div>

          <form onSubmit={onUpload} style={{ display: "grid", gap: 12 }}>
            <input
              type="file"
              accept="image/png,image/jpeg"
              multiple
              onChange={(e) =>
                setFiles(Array.from(e.target.files || []))
              }
            />

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: 12,
                borderRadius: 12,
                background: "#1A73E8",
                color: "white",
                border: "none",
                fontWeight: 800,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Uploading..." : "Upload Images"}
            </button>

            {files.length > 0 && (
              <div style={{ color: "#374151" }}>
                Selected: <b>{files.length}</b> file(s)
              </div>
            )}

            {status.msg && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  background:
                    status.type === "success" ? "#ECFDF3" : "#FEF2F2",
                }}
              >
                <b
                  style={{
                    color:
                      status.type === "success" ? "#166534" : "#991B1B",
                  }}
                >
                  {status.type === "success" ? "Success: " : "Error: "}
                </b>
                {status.msg}
              </div>
            )}
          </form>

          <div style={{ marginTop: 16 }}>
            <Link to="/teachers" style={{ color: "#1A73E8", fontWeight: 700 }}>
              Go to Teacher List
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
