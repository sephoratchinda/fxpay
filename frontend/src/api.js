const BASE = import.meta.env.VITE_API_URL || "/api";
const KEY = "fxpay_tokens";

export const tokens = {
  get: () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } },
  set: (t) => localStorage.setItem(KEY, JSON.stringify(t)),
  clear: () => localStorage.removeItem(KEY),
};

async function call(method, path, body, retry = true) {
  const t = tokens.get();
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t.access}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && t?.refresh && retry && !path.startsWith("/auth/")) {
    const r = await fetch(`${BASE}/auth/refresh/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: t.refresh }) });
    if (r.ok) { tokens.set({ ...t, access: (await r.json()).access }); return call(method, path, body, false); }
    tokens.clear(); window.location.reload();
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || data.detail || Object.entries(data).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join("; ") || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  get: (p) => call("GET", p),
  post: (p, b) => call("POST", p, b || {}),
  del: (p) => call("DELETE", p),
};

export async function login(username, password) {
  tokens.set(await call("POST", "/auth/login/", { username, password }));
}
export async function register(username, email, password) {
  await call("POST", "/auth/register/", { username, email, password });
  await login(username, password);
}
