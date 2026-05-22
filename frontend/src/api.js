import { clearAuth, getToken } from "./authStorage";

const rawBase = import.meta.env.VITE_API_BASE_URL;
const apiBase =
  typeof rawBase === "string" && rawBase.trim()
    ? rawBase.trim().replace(/\/$/, "")
    : "";

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase}${p}`;
}

function authHeaders(extra = {}) {
  const token = getToken();
  const headers = { ...extra };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseError(res) {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  if (detail != null) return JSON.stringify(detail);
  return res.statusText;
}

async function handleAuthResponse(res) {
  if (res.status === 401) {
    clearAuth();
    window.location.reload();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postSignup(body) {
  const res = await fetch(apiUrl("/api/auth/signup"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postLogin(body) {
  const res = await fetch(apiUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchMe() {
  const res = await fetch(apiUrl("/api/auth/me"), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function postAsk(question) {
  const res = await fetch(apiUrl("/api/ask"), {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question }),
  });
  return handleAuthResponse(res);
}

export async function postChat(messages) {
  const res = await fetch(apiUrl("/api/chat"), {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ messages }),
  });
  return handleAuthResponse(res);
}

export async function postPlan(question) {
  const res = await fetch(apiUrl("/api/plan"), {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question }),
  });
  return handleAuthResponse(res);
}

export async function fetchHealth() {
  const res = await fetch(apiUrl("/health"));
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}
