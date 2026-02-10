const BASE = "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY;

function withAuth(headers = {}) {
  if (!API_KEY) return headers;
  return { ...headers, "X-API-Key": API_KEY };
}

export async function fetchTeachers() {
  const r = await fetch(`${BASE}/teachers`, { headers: withAuth() });
  return r.json();
}

export async function fetchAttendance(date) {
  const url = date ? `${BASE}/attendance?date=${encodeURIComponent(date)}` : `${BASE}/attendance`;
  const r = await fetch(url, { headers: withAuth() });
  return r.json();
}

export async function fetchSummary(date) {
  const r = await fetch(`${BASE}/attendance/summary?date=${encodeURIComponent(date)}`, {
    headers: withAuth(),
  });
  return r.json();
}

export async function createTeacher(payload) {
  const r = await fetch(`${BASE}/teachers`, {
    method: "POST",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to create teacher");
  return data;
}

export async function uploadFaces(teacherId, files) {
  const form = new FormData();
  for (const f of files) form.append("files", f);

  const r = await fetch(`${BASE}/teachers/${teacherId}/faces`, {
    method: "POST",
    headers: withAuth(),
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

export async function recognizeFrame(blob, sessionId = null) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");

  const headers = withAuth();
  if (sessionId) headers["X-Session-Id"] = sessionId;

  const r = await fetch(`${BASE}/attendance/recognize`, {
    method: "POST",
    headers,
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Recognition failed");
  return data;
}

export async function fetchTeacherById(id) {
  const r = await fetch(`${BASE}/teachers/${id}`, { headers: withAuth() });
  return r.json();
}

export async function enrollWithFaces({ full_name, department, employee_id, files }) {
  const form = new FormData();
  form.append("full_name", full_name);
  form.append("department", department);
  form.append("employee_id", employee_id);
  for (const f of files) form.append("files", f);

  const r = await fetch(`${BASE}/enroll`, {
    method: "POST",
    headers: withAuth(),
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d) => d.msg || d.message || "Invalid input").join(", ")
      : data.detail;
    throw new Error(detail || "Enrollment failed");
  }
  return data;
}

export async function fetchTrainStatus() {
  const r = await fetch(`${BASE}/train/status`, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch training status");
  return data;
}

export async function runTraining() {
  const r = await fetch(`${BASE}/train/run`, { method: "POST", headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to start training");
  return data;
}

export async function resetAttendance() {
  const r = await fetch(`${BASE}/admin/reset/attendance`, { method: "POST", headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to reset attendance");
  return data;
}

export async function hardReset() {
  const r = await fetch(`${BASE}/admin/reset/hard`, { method: "POST", headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Hard reset failed");
  return data;
}

export async function fetchTeacherDTR(teacherId, month = null) {
  const qs = month ? `?month=${encodeURIComponent(month)}` : "";
  const r = await fetch(`${BASE}/teachers/${teacherId}/dtr${qs}`, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch DTR");
  return data;
}

export async function deleteAttendanceLog(logId) {
  const r = await fetch(`${BASE}/attendance/${logId}`, { method: "DELETE", headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to delete log entry");
  return data;
}
