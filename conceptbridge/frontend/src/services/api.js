const BASE = "/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  health: () => request("/health"),
  overview: () => request("/analytics/overview"),
  students: () => request("/students"),
  profiles: () => request("/profiles"),
  graph: () => request("/graph"),
  rebuildGraph: () => request("/graph/rebuild", { method: "POST" }),
  currentMatch: () => request("/matching/current"),
  matchHistory: () => request("/matching/history"),
  runMatching: (run_id) =>
    request("/matching/run", { method: "POST", body: JSON.stringify({ run_id }) }),
  approve: (id) =>
    request(`/matching/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ decided_by: "instructor", reason: "approved in UI" }),
    }),
  reject: (id) =>
    request(`/matching/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ decided_by: "instructor", reason: "rejected in UI" }),
    }),
  generateSession: (match_id) =>
    request("/sessions/generate", { method: "POST", body: JSON.stringify({ match_id }) }),
  run: (run_id) => request(`/runs/${run_id}`),
  runHistory: (run_id) => request(`/runs/${run_id}/history`),
};
