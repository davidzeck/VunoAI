/**
 * Tabs component — wire up a .tab-bar + .tab-panel set.
 * Usage: initTabs(containerEl)
 */
export function initTabs(container) {
  const tabs   = [...container.querySelectorAll(".tab")];
  const panels = [...container.querySelectorAll(".tab-panel")];

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const panel = container.querySelector(`#tab-${target}`);
      if (panel) panel.classList.add("active");
    });
  });
}
