import { api } from "../api.js";
import { notify } from "../components/toast.js";
import { pollTask } from "../components/poll.js";
import { initTabs } from "../components/tabs.js";
import { skeletonLines } from "../components/skeleton.js";
import { riskBadge, statusBadge, intentLabel } from "../components/badge.js";
import { getTaskCodeFromURL, formatDate, escapeHtml, qs } from "../utils.js";
import { PROCESSING_STATUSES } from "../config.js";

const code = getTaskCodeFromURL();
if (!code) window.location.href = "dashboard.html";

// DOM refs
const clarificationBanner = qs("#clarification-banner");
const clarificationNote   = qs("#clarification-note");
const rejectionBanner     = qs("#rejection-banner");
const rejectionReason  = qs("#rejection-reason");
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
const statusActionEl   = qs("#status-action");
const tabsContainer    = qs("#messages-section");

async function load() {
  try {
    const task = await api.tasks.get(code);
    render(task);

    // Only poll while the AI pipeline is still running.
    // steps.length > 0 means the pipeline finished — don't poll even if status
    // was manually changed back to in_progress by an ops agent.
    const pipelineStillRunning = PROCESSING_STATUSES.includes(task.status) && !task.steps?.length;
    if (pipelineStillRunning) {
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

  // Clarification banner
  if (task.clarification_note && task.status !== "rejected") {
    clarificationBanner?.classList.remove("hidden");
    if (clarificationNote) clarificationNote.textContent = task.clarification_note;
  } else {
    clarificationBanner?.classList.add("hidden");
  }

  // Rejection / rate-limit banner
  const isRateLimit = task.status === "failed" && task.error_detail?.startsWith("rate_limit_exceeded");
  if (task.status === "rejected" || isRateLimit) {
    rejectionBanner?.classList.remove("hidden");
    const icon  = rejectionBanner?.querySelector(".rejection-banner__icon");
    const title = rejectionBanner?.querySelector(".rejection-banner__title");
    if (isRateLimit) {
      if (icon)  icon.textContent  = "⏳";
      if (title) title.textContent = "Rate Limit Reached";
      if (rejectionReason) rejectionReason.textContent =
        "Our AI providers are temporarily at capacity. This request will be retried automatically — check back in a few minutes.";
    } else {
      if (icon)  icon.textContent  = "✕";
      if (title) title.textContent = "Request Out of Scope";
      if (rejectionReason) rejectionReason.textContent = task.error_detail || "This request is outside Vunoh's service scope.";
    }
  } else {
    rejectionBanner?.classList.add("hidden");
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

  // Steps — interactive checklist (read-only when task is terminal)
  if (stepsEl) {
    if (task.steps?.length) {
      const isTerminal = ["completed", "failed", "rejected"].includes(task.status);
      stepsEl.innerHTML = task.steps.map((s, i) => `
        <li class="step-item ${s.completed ? "step-item--done" : ""}">
          <input type="checkbox"
            class="step-check"
            data-order="${s.order}"
            ${s.completed  ? "checked"  : ""}
            ${isTerminal   ? "disabled" : ""}
          />
          <span class="step-number">${i + 1}</span>
          <span>${escapeHtml(s.description)}</span>
        </li>`).join("");

      // Attach listeners only when task is not terminal
      if (!isTerminal) {
        stepsEl.querySelectorAll(".step-check").forEach(cb => {
          cb.addEventListener("change", async () => {
            cb.disabled = true;
            try {
              const result = await api.tasks.completeStep(
                code, parseInt(cb.dataset.order, 10), cb.checked,
              );
              if (result.task_status !== task.status) {
                // Task auto-completed — re-fetch and re-render the whole card
                const updated = await api.tasks.get(code);
                render(updated);
              } else {
                cb.closest(".step-item").classList.toggle("step-item--done", cb.checked);
                cb.disabled = false;
              }
            } catch (err) {
              notify.error(err.message || "Failed to update step.");
              cb.checked = !cb.checked;
              cb.disabled = false;
            }
          });
        });
      }
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

  // Status update — available for all non-rejected tasks
  if (statusActionEl) {
    if (task.status === "rejected") {
      statusActionEl.innerHTML = "";
    } else {
      const STATUS_OPTIONS = [
        { value: "pending",     label: "Pending" },
        { value: "in_progress", label: "In Progress" },
        { value: "completed",   label: "Completed" },
        { value: "failed",      label: "Failed" },
      ];
      statusActionEl.innerHTML = `
        <div style="margin-top:var(--sp-4);padding-top:var(--sp-4);border-top:1px solid var(--border-light);">
          <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:var(--sp-2);">Update Status</label>
          <div style="display:flex;gap:var(--sp-2);align-items:center;">
            <select id="status-select" style="flex:1;font-size:13px;">
              ${STATUS_OPTIONS.map(o =>
                `<option value="${o.value}" ${task.status === o.value ? "selected" : ""}>${o.label}</option>`
              ).join("")}
            </select>
            <button id="status-save-btn" class="btn btn-outline btn--sm">Save</button>
          </div>
        </div>`;

      qs("#status-save-btn")?.addEventListener("click", async () => {
        const sel       = qs("#status-select");
        const newStatus = sel?.value;
        if (!newStatus || newStatus === task.status) return;
        const saveBtn = qs("#status-save-btn");
        saveBtn.disabled    = true;
        saveBtn.textContent = "Saving…";
        try {
          await api.tasks.status(code, { status: newStatus });
          notify.success("Status updated.");
          const updated = await api.tasks.get(code);
          render(updated);
        } catch (err) {
          notify.error(err.message || "Failed to update status.");
          saveBtn.disabled    = false;
          saveBtn.textContent = "Save";
        }
      });
    }
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

// Send buttons
["whatsapp", "email"].forEach(channel => {
  const btn      = qs(`#send-btn-${channel}`);
  const inp      = qs(`#send-recipient-${channel}`);
  const statusEl = qs(`#send-status-${channel}`);

  btn?.addEventListener("click", async () => {
    const recipient = inp?.value.trim();
    if (!recipient) { notify.error("Enter a recipient first."); return; }
    btn.disabled    = true;
    btn.textContent = "Sending…";
    try {
      await api.tasks.send(code, channel, recipient);
      if (statusEl) { statusEl.textContent = "✓ Queued"; statusEl.classList.add("send-status--sent"); }
      notify.success(`${channel === "whatsapp" ? "WhatsApp" : "Email"} message queued.`);
    } catch (err) {
      notify.error(err.message || "Failed to send.");
      btn.disabled    = false;
      btn.textContent = `Send via ${channel === "whatsapp" ? "WhatsApp" : "Email"}`;
    }
  });
});

load();
