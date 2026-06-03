export const API_BASE = "/api/v1";

let memoryToken = "";

export async function getToken(): Promise<string> {
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get("token");
  if (urlToken) {
    console.log("[Auth] Token source: URL");
    try { localStorage.setItem("nexus_token", urlToken); } catch (_) {}
    memoryToken = urlToken;
    return urlToken;
  }

  if (memoryToken) {
    return memoryToken;
  }

  if (import.meta.env.DEV) {
    try {
      const resp = await fetch("/api/v1/auth/token");
      if (resp.ok) {
        const data = await resp.json();
        if (data.token) {
          console.log("[Auth] Token source: GET /api/v1/auth/token");
          memoryToken = data.token;
          try { localStorage.setItem("nexus_token", data.token); } catch (_) {}
          return data.token;
        }
      }
    } catch (_) {}
  }

  const metaToken = document.querySelector('meta[name="nexus-token"]')?.getAttribute("content");
  if (metaToken) {
    console.log("[Auth] Token source: meta tag");
    memoryToken = metaToken;
    try { localStorage.setItem("nexus_token", metaToken); } catch (_) {}
    return metaToken;
  }

  try {
    const lsToken = localStorage.getItem("nexus_token");
    if (lsToken) {
      console.log("[Auth] Token source: localStorage");
      memoryToken = lsToken;
      return lsToken;
    }
  } catch (_) {}

  console.log("[Auth] Token source: none");
  return "";
}

export function clearTokenCache(): void {
  memoryToken = "";
  try { localStorage.removeItem("nexus_token"); } catch (_) {}
}

export async function apiUrl(path: string, params: Record<string, string | number> = {}): Promise<string> {
  const p = new URLSearchParams({ token: await getToken(), ...params as any });
  return `${API_BASE}${path}?${p.toString()}`;
}

export async function apiFetch(path: string, params: Record<string, string | number> = {}): Promise<any> {
  let resp = await fetch(await apiUrl(path, params));
  if (resp.status === 403 && import.meta.env.DEV) {
    clearTokenCache();
    resp = await fetch(await apiUrl(path, params));
  }
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event("auth_error"));
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

export async function apiPost(path: string, body: any = {}): Promise<any> {
  let url = `${API_BASE}${path}?token=${encodeURIComponent(await getToken())}`;
  let reqConfig = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  let resp = await fetch(url, reqConfig);
  if (resp.status === 403 && import.meta.env.DEV) {
    clearTokenCache();
    url = `${API_BASE}${path}?token=${encodeURIComponent(await getToken())}`;
    resp = await fetch(url, reqConfig);
  }
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event("auth_error"));
    let detail = "";
    const textBody = await resp.text();
    try {
      const errBody = JSON.parse(textBody);
      detail = errBody.detail || errBody.error || "";
    } catch (_) {
      detail = textBody;
    }
    throw new Error(`${resp.status}: ${detail || resp.statusText}`);
  }
  return resp.json();
}

export async function apiDelete(path: string): Promise<any> {
  let url = `${API_BASE}${path}?token=${encodeURIComponent(await getToken())}`;
  let reqConfig = { method: "DELETE" };
  let resp = await fetch(url, reqConfig);
  if (resp.status === 403 && import.meta.env.DEV) {
    clearTokenCache();
    url = `${API_BASE}${path}?token=${encodeURIComponent(await getToken())}`;
    resp = await fetch(url, reqConfig);
  }
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event("auth_error"));
    let detail = "";
    const textBody = await resp.text();
    try {
      const errBody = JSON.parse(textBody);
      detail = errBody.detail || errBody.error || "";
    } catch (_) {
      detail = textBody;
    }
    throw new Error(`${resp.status}: ${detail || resp.statusText}`);
  }
  return resp.json();
}

export const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/v1/cost/live`;
