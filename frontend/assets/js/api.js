import { API_BASE } from "./config.js";

async function request(method, path, body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  };
  if (body) options.body = JSON.stringify(body);

  const resp = await fetch(`${API_BASE}/api${path}`, options);

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || err.detail || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  tasks: {
    list:   (params = {}) => request("GET", `/tasks/?${new URLSearchParams(params)}`),
    create: (body)         => request("POST", "/tasks/", body),
    get:    (code)         => request("GET", `/tasks/${code}/`),
    status: (code, body)   => request("PATCH", `/tasks/${code}/status/`, body),
    messages: (code)       => request("GET", `/tasks/${code}/messages/`),
  },
};
