const API_BASE = "http://localhost:8000/api";

export async function createSession(language = "hi") {
  const res = await fetch(`${API_BASE}/session/create?language=${encodeURIComponent(language)}`, {
    method: "POST",
  });
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API_BASE}/session/${encodeURIComponent(sessionId)}`);
  return res.json();
}

export async function sendMessage(sessionId, message, source = "text") {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, source }),
  });
  return res.json();
}

export async function uploadDocument(sessionId, file) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);
  const res = await fetch(`${API_BASE}/document/upload`, {
    method: "POST",
    body: form,
  });
  return res.json();
}

export async function generateForm(sessionId, schemeId) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("scheme_id", schemeId);
  const res = await fetch(`${API_BASE}/form/generate`, {
    method: "POST",
    body: form,
  });
  return res.json();
}

export async function getFormPreview(sessionId, schemeId) {
  const res = await fetch(
    `${API_BASE}/form/preview/${encodeURIComponent(schemeId)}?session_id=${encodeURIComponent(sessionId)}`
  );
  return res.json();
}

export async function submitFilledForm(sessionId, schemeId, filledData) {
  const res = await fetch(`${API_BASE}/form/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, scheme_id: schemeId, filled_data: filledData }),
  });
  return res.json();
}

export async function listSchemes() {
  const res = await fetch(`${API_BASE}/schemes`);
  return res.json();
}

export function getFormDownloadUrl(filename) {
  return `http://localhost:8000/files/forms/${encodeURIComponent(filename)}`;
}
