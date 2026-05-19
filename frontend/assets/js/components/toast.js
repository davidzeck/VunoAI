let container = null;

function getContainer() {
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

export function toast(message, type = "info", duration = 4000) {
  const c = getContainer();
  const t = document.createElement("div");
  t.className = `toast toast--${type}`;
  t.textContent = message;
  c.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

export const notify = {
  success: (msg) => toast(msg, "success"),
  error:   (msg) => toast(msg, "error"),
  info:    (msg) => toast(msg, "info"),
};
