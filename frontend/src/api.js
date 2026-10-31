const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function j(path, opts = {}) {
  const r = await fetch(BASE + path, opts);
  if (!r.ok) {
    let msg = `${path} failed (${r.status})`;
    try {
      const err = await r.json();
      if (err.detail) msg = err.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  return r.json();
}

export const login = (username, password) =>
  j("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

export const getGraph = () => j("/api/graph");
export const getCases = () => j("/api/cases");
export const getCase = (id) => j(`/api/cases/${id}`);
export const getReport = (id, refresh = false) => j(`/api/cases/${id}/report?refresh=${refresh}`, { method: "POST" });
export const getPipeline = () => j("/api/pipeline");
