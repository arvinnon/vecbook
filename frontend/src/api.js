const BASE = "http://localhost:8000";

export async function fetchTeachers() {
  const r = await fetch(`${BASE}/teachers`);
  return r.json();
}

export async function fetchAttendance(date) {
  const url = date ? `${BASE}/attendance?date=${encodeURIComponent(date)}` : `${BASE}/attendance`;
  const r = await fetch(url);
  return r.json();
}

export async function fetchSummary(date) {
  const r = await fetch(`${BASE}/attendance/summary?date=${encodeURIComponent(date)}`);
  return r.json();
}

export async function createTeacher(payload) {
  const r = await fetch(`${BASE}/teachers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

export async function recognizeFrame(blob) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");

  const r = await fetch(`${BASE}/attendance/recognize`, {
    method: "POST",
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Recognition failed");
  return data;
}

export async function fetchTeacherById(id) {
  const r = await fetch(`${BASE}/teachers/${id}`);
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
    body: form,
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Enrollment failed");
  return data;
}

export async function fetchTrainStatus() {
  const r = await fetch(`${BASE}/train/status`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch training status");
  return data;
}

export async function runTraining() {
  const r = await fetch(`${BASE}/train/run`, { method: "POST" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to start training");
  return data;
}

export async function resetAttendance() {
  const r = await fetch(`${BASE}/admin/reset/attendance`, { method: "POST" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to reset attendance");
  return data;
}

export async function hardReset() {
  const r = await fetch(`${BASE}/admin/reset/hard`, { method: "POST" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Hard reset failed");
  return data;
}

export async function fetchTeacherDTR(teacherId, month = null) {
  const qs = month ? `?month=${encodeURIComponent(month)}` : "";
  const r = await fetch(`${BASE}/teachers/${teacherId}/dtr${qs}`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch DTR");
  return data;
}
