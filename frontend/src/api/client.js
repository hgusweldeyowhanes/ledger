const ACCESS = "ledger_access";
const REFRESH = "ledger_refresh";

export function getAccess() {
  return localStorage.getItem(ACCESS);
}

export function getRefresh() {
  return localStorage.getItem(REFRESH);
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

async function refreshAccess() {
  const refresh = getRefresh();
  if (!refresh) return null;
  const res = await fetch("/api/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = await res.json();
  setTokens({ access: data.access });
  return data.access;
}

export async function api(path, { method = "GET", body, formData, auth = true, headers = {} } = {}) {
  const opts = {
    method,
    headers: { ...headers },
  };
  if (formData instanceof FormData) {
    opts.body = formData;
    // Let the browser set multipart boundary — do not set Content-Type
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (auth) {
    const token = getAccess();
    if (token) opts.headers.Authorization = `Bearer ${token}`;
  }

  let res = await fetch(path.startsWith("/") ? path : `/api/${path}`, opts);
  if (res.status === 401 && auth && getRefresh()) {
    const next = await refreshAccess();
    if (next) {
      opts.headers.Authorization = `Bearer ${next}`;
      res = await fetch(path.startsWith("/") ? path : `/api/${path}`, opts);
    }
  }

  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const err = new Error(data?.detail || data?.error || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}
