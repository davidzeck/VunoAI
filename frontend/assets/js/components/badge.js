import { formatIntent, formatStatus, formatRisk } from "../utils.js";

export function riskBadge(level) {
  if (!level) return '<span style="color:var(--text-muted)">—</span>';
  return `<span class="badge badge-risk-${level}">${formatRisk(level)}</span>`;
}

export function statusBadge(status) {
  if (!status) return '<span style="color:var(--text-muted)">—</span>';
  return `<span class="badge badge-dot badge-status-${status}">${formatStatus(status)}</span>`;
}

export function intentLabel(intent) {
  if (!intent) return '<span style="color:var(--text-muted)">—</span>';
  return `<div class="intent-label"><span>${formatIntent(intent)}</span></div>`;
}

export function taskCodeEl(code) {
  return `<span class="task-code">${code}</span>`;
}
