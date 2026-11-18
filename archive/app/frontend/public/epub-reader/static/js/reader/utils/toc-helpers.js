import { queryAll } from "./dom-helpers.js";

export function flattenToc(items, level = 0) {
  if (!Array.isArray(items) || !items.length) return [];

  return items.flatMap((item) => {
    const current = {
      ...item,
      level
    };

    return [current, ...flattenToc(item.subitems || [], level + 1)];
  });
}

export function renderToc(container, items) {
  if (!container) return;

  const tocMarkup = items
    .map((item, index) => {
      const selectedClass = index === 0 ? "selected" : "";
      const marginLeft = 25 * item.level;
      const safeLabel = escapeHtml(item.label || "");
      const safeHref = escapeHtml(item.href || "");

      return `
        <div class="slide-contents-item">
          <button type="button" class="slide-contents-item-label ${selectedClass}" style="margin-left: ${marginLeft}px" title="${escapeHtml(
            item.label || ""
          )}" data-href="${safeHref}" aria-label="${safeLabel}" aria-current="${selectedClass ? "true" : "false"}">${safeLabel}</button>
          <span class="slide-contents-item-page"></span>
        </div>
      `;
    })
    .join("");

  container.innerHTML = tocMarkup;
}

export function syncSelectedTocItem(currentHref) {
  const tocRows = queryAll(".slide-contents-item");

  tocRows.forEach((row) => {
    const label = row.querySelector(".slide-contents-item-label");
    if (!label) return;

    const isSelected = getItemHref(label) === currentHref;
    label.classList.toggle("selected", isSelected);
    label.setAttribute("aria-current", isSelected ? "true" : "false");
  });
}

export function getItemHref(element) {
  if (!element) return "";
  return element.getAttribute("data-href") || element.getAttribute("href") || "";
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
