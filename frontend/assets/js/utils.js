import { INTENT_LABELS, STATUS_LABELS, RISK_LABELS } from "./config.js";

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-KE", {
    day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatIntent(intent) {
  return INTENT_LABELS[intent] || intent || "—";
}

export function formatStatus(status) {
  return STATUS_LABELS[status] || status || "—";
}

export function formatRisk(level) {
  return RISK_LABELS[level] || level || "—";
}

export function getTaskCodeFromURL() {
  return new URLSearchParams(window.location.search).get("code");
}

export function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = String(str ?? "");
  return d.innerHTML;
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "style") Object.assign(node.style, v);
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child == null) continue;
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return [...root.querySelectorAll(selector)];
}
