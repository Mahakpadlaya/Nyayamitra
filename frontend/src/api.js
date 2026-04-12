const rawBase = import.meta.env.VITE_API_BASE_URL;
const apiBase =
  typeof rawBase === "string" && rawBase.trim()
    ? rawBase.trim().replace(/\/$/, "")
    : "";

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase}${p}`;
}

async function parseError(res) {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  if (detail != null) return JSON.stringify(detail);
  return res.statusText;
}

export async function postAsk(question) {
  const res = await fetch(apiUrl("/api/ask"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postChat(messages) {
  const res = await fetch(apiUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postPlan(question) {
  const res = await fetch(apiUrl("/api/plan"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(apiUrl("/health"));
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}
