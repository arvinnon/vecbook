const BASE = "http://localhost:8000";
const SESSION_TOKEN_KEY = "vecbook_session_token";

function getStorage() {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getSessionToken() {
  const storage = getStorage();
  if (!storage) return "";
  return storage.getItem(SESSION_TOKEN_KEY) || "";
}

export function hasSession() {
  return Boolean(getSessionToken());
}

export function clearSession() {
  const storage = getStorage();
  if (!storage) return;
  storage.removeItem(SESSION_TOKEN_KEY);
}

function setSessionToken(token) {
  const storage = getStorage();
  if (!storage) return;
  storage.setItem(SESSION_TOKEN_KEY, token);
}

function withAuth(headers = {}) {
  const token = getSessionToken();
  if (!token) return headers;
  return { ...headers, Authorization: `Bearer ${token}` };
}

export async function createSession({ username, password }) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Authentication failed");
  if (!data.access_token) throw new Error("Invalid auth response");
  setSessionToken(data.access_token);
  return data;
}

export async function fetchSessionMe() {
  const r = await fetch(`${BASE}/auth/me`, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Unauthorized");
  return data;
}

export async function fetchTeachers() {
  const r = await fetch(`${BASE}/teachers`, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch teachers");
  if (!Array.isArray(data)) throw new Error("Invalid teachers response");
  return data;
}

export async function fetchAttendance(date) {
  const url = date ? `${BASE}/attendance?date=${encodeURIComponent(date)}` : `${BASE}/attendance`;
  const r = await fetch(url, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch attendance");
  if (!Array.isArray(data)) throw new Error("Invalid attendance response");
  return data;
}

export async function fetchRecognitionConfig() {
  const r = await fetch(`${BASE}/config/recognition`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch recognition config");
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Invalid recognition config response");
  }
  return data;
}

export async function fetchScanEvents(filters = {}) {
  const params = new URLSearchParams();
  if (filters.date) params.set("date", String(filters.date));
  if (filters.teacher_id != null && String(filters.teacher_id).trim() !== "") {
    params.set("teacher_id", String(filters.teacher_id).trim());
  }
  if (filters.decision_code) params.set("decision_code", String(filters.decision_code));
  if (filters.requires_review != null && filters.requires_review !== "") {
    params.set("requires_review", String(filters.requires_review));
  }
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));

  const qs = params.toString();
  const url = qs ? `${BASE}/admin/scan-events?${qs}` : `${BASE}/admin/scan-events`;
  const r = await fetch(url, { headers: withAuth() });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch scan audit history");
  if (!data || typeof data !== "object" || !Array.isArray(data.rows)) {
    throw new Error("Invalid scan events response");
  }
  return data;
}

export async function fetchSummary(date) {
  const r = await fetch(`${BASE}/attendance/summary?date=${encodeURIComponent(date)}`, {
    headers: withAuth(),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch summary");
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Invalid summary response");
  }
  return data;
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
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Failed to fetch teacher");
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Invalid teacher response");
  }
  return data;
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
