export function skeletonLines(count = 4) {
  const widths = ["60%", "100%", "80%", "45%", "70%", "90%"];
  return Array.from({ length: count }, (_, i) =>
    `<div class="skeleton" style="width:${widths[i % widths.length]};height:12px;margin-bottom:10px;"></div>`
  ).join("");
}
