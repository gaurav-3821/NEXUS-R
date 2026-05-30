const API_BASE = "/api/v1";

function getToken(): string {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    try { localStorage.setItem("nexus_token", token); } catch (_) {}
    return token;
  }
  try { return localStorage.getItem("nexus_token") || ""; } catch (_) { return ""; }
}

export const TOKEN = getToken();

export function apiUrl(path: string, params: Record<string, string | number> = {}): string {
  const p = new URLSearchParams({ token: TOKEN, ...params as any });
  return `${API_BASE}${path}?${p.toString()}`;
}

export async function apiFetch(path: string, params: Record<string, string | number> = {}): Promise<any> {
  const resp = await fetch(apiUrl(path, params));
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event("auth_error"));
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

export async function apiPost(path: string, body: any = {}): Promise<any> {
  const url = `${API_BASE}${path}?token=${encodeURIComponent(TOKEN)}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event("auth_error"));
    let detail = "";
    try {
      const errBody = await resp.json();
      detail = errBody.detail || errBody.error || "";
    } catch (_) {
      detail = await resp.text();
    }
    throw new Error(`${resp.status}: ${detail || resp.statusText}`);
  }
  return resp.json();
}

export const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/v1/cost/live`;
