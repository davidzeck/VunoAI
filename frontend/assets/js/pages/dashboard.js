import { api } from "../api.js";
import { notify } from "../components/toast.js";
import { riskBadge, statusBadge, intentLabel, taskCodeEl } from "../components/badge.js";
import { formatDate, qs } from "../utils.js";

const tableBody   = qs("#task-tbody");
const totalEl     = qs("#stat-total");
const pendingEl   = qs("#stat-pending");
const highRiskEl  = qs("#stat-high-risk");
const filterForm  = qs("#filter-form");
const clearBtn    = qs("#clear-filters");

async function loadTasks() {
  const params = Object.fromEntries(
    [...new URLSearchParams(window.location.search).entries()]
      .filter(([, v]) => v !== "")
  );

  tableBody.innerHTML = skeletonRows(5);

  try {
    const tasks = await api.tasks.list(params);
    renderStats(tasks);
    renderTable(tasks);
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="6" class="empty-state">Failed to load tasks. Is the server running?</td></tr>`;
    notify.error(err.message);
  }
}

function renderStats(tasks) {
  if (totalEl)    totalEl.textContent    = tasks.length;
  if (pendingEl)  pendingEl.textContent  = tasks.filter(t => ["pending","in_progress"].includes(t.status)).length;
  if (highRiskEl) highRiskEl.textContent = tasks.filter(t => t.risk_level === "high").length;
}

function renderTable(tasks) {
  if (!tasks.length) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6">
          <div class="empty-state">
            <div style="font-size:32px">📋</div>
            <div style="font-weight:600;margin-top:12px">No tasks found</div>
            <p><a href="index.html">Submit your first request</a></p>
          </div>
        </td>
      </tr>`;
    return;
  }

  const STATUS_OPTIONS = ["pending", "in_progress", "completed", "failed"];

  tableBody.innerHTML = tasks.map(t => {
    const isRejected = t.status === "rejected";
    const opts = isRejected
      ? `<option value="rejected" selected>Rejected</option>`
      : STATUS_OPTIONS.map(s =>
          `<option value="${s}" ${t.status === s ? "selected" : ""}>${
            s === "in_progress" ? "In Progress" : s.charAt(0).toUpperCase() + s.slice(1)
          }</option>`
        ).join("");
    return `
    <tr class="table-row-link" data-href="task.html?code=${t.task_code}">
      <td>${taskCodeEl(t.task_code)}</td>
      <td>${intentLabel(t.intent)}</td>
      <td onclick="event.stopPropagation()">
        <select class="status-select-inline" data-code="${t.task_code}" data-current="${t.status}" ${isRejected ? "disabled" : ""}>
          ${opts}
        </select>
      </td>
      <td>${riskBadge(t.risk_level)}${t.risk_score != null ? `<span class="risk-score-inline">${t.risk_score}</span>` : ""}</td>
      <td class="hide-mobile" style="color:var(--text-secondary);font-size:13px">${t.employee_assignment || "—"}</td>
      <td class="hide-mobile" style="color:var(--text-muted);font-size:12px">${formatDate(t.created_at)}</td>
    </tr>`;
  }).join("");

  // Status select: save on change, revert on failure
  tableBody.querySelectorAll(".status-select-inline").forEach(sel => {
    sel.addEventListener("change", async (e) => {
      e.stopPropagation();
      const code    = sel.dataset.code;
      const prev    = sel.dataset.current;
      const newVal  = sel.value;
      sel.disabled  = true;
      try {
        await api.tasks.status(code, { status: newVal });
        sel.dataset.current = newVal;
        notify.success("Status updated.");
      } catch (err) {
        sel.value = prev;
        notify.error(err.message || "Failed to update status.");
      } finally {
        sel.disabled = false;
      }
    });
  });

  // Make rows clickable (excluding the status cell)
  tableBody.querySelectorAll(".table-row-link").forEach(row => {
    row.style.cursor = "pointer";
    row.addEventListener("click", () => window.location.href = row.dataset.href);
  });
}

function skeletonRows(n) {
  return Array.from({ length: n }, () => `
    <tr>
      ${Array.from({ length: 6 }, () =>
        `<td><div class="skeleton" style="height:12px;width:80%"></div></td>`
      ).join("")}
    </tr>
  `).join("");
}

// Filters: auto-submit on select change
filterForm?.querySelectorAll("select").forEach(sel => {
  sel.addEventListener("change", () => filterForm.submit());
});

// Sync filter selects from URL
const params = new URLSearchParams(window.location.search);
filterForm?.querySelectorAll("select").forEach(sel => {
  if (params.has(sel.name)) sel.value = params.get(sel.name);
});
filterForm?.querySelectorAll("input").forEach(inp => {
  if (params.has(inp.name)) inp.value = params.get(inp.name);
});

// Clear filters
clearBtn?.addEventListener("click", () => window.location.href = "dashboard.html");

loadTasks();
