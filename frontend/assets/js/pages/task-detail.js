import { api } from "../api.js";
import { notify } from "../components/toast.js";
import { pollTask } from "../components/poll.js";
import { initTabs } from "../components/tabs.js";
import { skeletonLines } from "../components/skeleton.js";
import { riskBadge, statusBadge, intentLabel } from "../components/badge.js";
import { getTaskCodeFromURL, formatDate, escapeHtml, qs } from "../utils.js";
import { PROCESSING_STATUSES, STATUS_LABELS } from "../config.js";

const code = getTaskCodeFromURL();
if (!code) window.location.href = "dashboard.html";

// DOM refs
const processingBanner = qs("#processing-banner");
const taskCodeEl       = qs("#task-code");
const taskStatusEl     = qs("#task-status");
const intentEl         = qs("#task-intent");
const requestQuote     = qs("#request-quote");
const riskScoreEl      = qs("#risk-score");
const riskLevelEl      = qs("#risk-level");
const riskBarEl        = qs("#risk-bar-fill");
const riskFlagsEl      = qs("#risk-flags");
const stepsEl          = qs("#steps-list");
const assignmentEl     = qs("#assignment");
const confidenceBarEl  = qs("#confidence-bar");
const confidenceValEl  = qs("#confidence-val");
const entitiesEl       = qs("#entities-grid");
const escalationBadge  = qs("#escalation-badge");
const msgWhatsApp      = qs("#msg-whatsapp");
const msgEmail         = qs("#msg-email");
const msgSms           = qs("#msg-sms");
const msgSmsCount      = qs("#msg-sms-count");
const historyEl        = qs("#history-list");
const statusSelect     = qs("#status-select");
const statusSaveBtn    = qs("#status-save");
const tabsContainer    = qs("#messages-section");

async function load() {
  try {
    const task = await api.tasks.get(code);
    render(task);

    if (PROCESSING_STATUSES.includes(task.status)) {
      processingBanner?.classList.remove("hidden");
      pollTask(code, {
        onDone: (done) => { render(done); processingBanner?.classList.add("hidden"); },
        onError: () => notify.error("Lost connection while polling."),
      });
    }
  } catch (err) {
    notify.error("Task not found or server unavailable.");
  }
}

function render(task) {
  // Header
  if (taskCodeEl)   taskCodeEl.textContent  = task.task_code;
  if (taskStatusEl) taskStatusEl.innerHTML  = statusBadge(task.status);
  if (intentEl)     intentEl.innerHTML      = intentLabel(task.intent);
  if (requestQuote) requestQuote.textContent = task.customer_request;
  if (escalationBadge) {
    escalationBadge.style.display = task.escalation_required ? "inline-flex" : "none";
  }

  // Risk card
  if (task.risk_score != null) {
    if (riskScoreEl)  riskScoreEl.textContent  = task.risk_score;
    if (riskLevelEl)  riskLevelEl.innerHTML    = riskBadge(task.risk_level);
    if (riskBarEl) {
      riskBarEl.style.width = `${task.risk_score}%`;
      riskBarEl.className   = `risk-bar__fill risk-bar__fill--${task.risk_level}`;
    }
    if (riskFlagsEl && task.risk_explanation?.length) {
      riskFlagsEl.innerHTML = task.risk_explanation
        .map(r => `<li class="flag-item">${escapeHtml(r)}</li>`).join("");
    }
  } else {
    if (riskScoreEl)  riskScoreEl.innerHTML = skeletonLines(3);
  }

  // Steps
  if (stepsEl) {
    if (task.steps?.length) {
      stepsEl.innerHTML = task.steps.map((s, i) => `
        <li class="step-item">
          <span class="step-number">${i + 1}</span>
          <span>${escapeHtml(s.description)}</span>
        </li>`).join("");
    } else {
      stepsEl.innerHTML = skeletonLines(4);
    }
  }

  // Assignment + confidence
  if (assignmentEl) {
    assignmentEl.textContent = task.employee_assignment || "Processing…";
  }
  if (task.ai_confidence != null) {
    const pct = Math.round(task.ai_confidence * 100);
    if (confidenceBarEl) confidenceBarEl.style.width = `${pct}%`;
    if (confidenceValEl) confidenceValEl.textContent = `${pct}%`;
  }

  // Entities
  if (entitiesEl && task.extracted_entities?.length) {
    entitiesEl.innerHTML = task.extracted_entities.map(e => `
      <div class="entity-item">
        <div class="entity-key">${escapeHtml(e.entity_key)}</div>
        <div class="entity-value">${escapeHtml(e.entity_value)}</div>
      </div>`).join("");
  }

  // Messages
  if (task.messages?.length) {
    const byChannel = Object.fromEntries(task.messages.map(m => [m.channel, m.content]));
    if (msgWhatsApp) msgWhatsApp.textContent = byChannel.whatsapp || "—";
    if (msgEmail)    msgEmail.textContent    = byChannel.email    || "—";
    if (msgSms) {
      msgSms.textContent = byChannel.sms || "—";
      if (msgSmsCount) msgSmsCount.textContent = `${(byChannel.sms || "").length} / 160 characters`;
    }
    if (tabsContainer) initTabs(tabsContainer);
  }

  // Status select
  if (statusSelect) {
    statusSelect.value = task.status;
    const canUpdate = !PROCESSING_STATUSES.includes(task.status);
    statusSelect.disabled  = !canUpdate;
    if (statusSaveBtn) statusSaveBtn.disabled = !canUpdate;
  }

  // History
  if (historyEl && task.history?.length) {
    historyEl.innerHTML = task.history.map(h => `
      <li class="timeline-item">
        <div class="timeline-dot timeline-dot--done"></div>
        <div>
          <span style="font-weight:500">${escapeHtml(h.from_status)}</span>
          <span style="color:var(--text-muted);margin:0 8px">→</span>
          <span style="font-weight:500;color:var(--accent-primary)">${escapeHtml(h.to_status)}</span>
          <span style="margin-left:12px;font-size:12px;color:var(--text-muted)">${formatDate(h.changed_at)}</span>
          ${h.note ? `<span style="margin-left:8px;font-size:12px;color:var(--text-secondary)">· ${escapeHtml(h.note)}</span>` : ""}
        </div>
      </li>`).join("");
  }
}

// Status update
statusSaveBtn?.addEventListener("click", async () => {
  const newStatus = statusSelect?.value;
  if (!newStatus) return;
  try {
    await api.tasks.status(code, { status: newStatus });
    notify.success("Status updated.");
    setTimeout(() => location.reload(), 800);
  } catch (err) {
    notify.error(err.message || "Failed to update status.");
  }
});

// Build status select options
if (statusSelect) {
  statusSelect.innerHTML = Object.entries(STATUS_LABELS)
    .map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
}

load();
