import { api } from "../api.js";
import { notify } from "../components/toast.js";
import { qs } from "../utils.js";

const form     = qs("#request-form");
const textarea = qs("#customer_request");
const submit   = qs("#submit-btn");
const chips    = [...document.querySelectorAll(".example-chip")];

chips.forEach(chip => {
  chip.addEventListener("click", () => {
    textarea.value = chip.textContent.trim();
    textarea.focus();
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = textarea.value.trim();
  if (!text) { notify.error("Please describe the customer request."); return; }

  submit.disabled = true;
  submit.textContent = "Processing…";

  try {
    const result = await api.tasks.create({ customer_request: text });
    notify.success("Request submitted — processing started.");
    setTimeout(() => {
      window.location.href = `task.html?code=${result.task_code}`;
    }, 600);
  } catch (err) {
    notify.error(err.message || "Failed to submit request.");
    submit.disabled = false;
    submit.textContent = "Process Request →";
  }
});
