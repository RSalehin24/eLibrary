import { queryAll } from "./dom-helpers.js";

export function flattenToc(items, level = 0, ancestorLabels = []) {
  if (!Array.isArray(items) || !items.length) return [];

  return items.flatMap((item) => {
    const current = {
      ...item,
      level,
      ancestorLabels: [...ancestorLabels],
    };

    const nextAncestors = [...ancestorLabels, item.label || ""];
    return [
      current,
      ...flattenToc(item.subitems || [], level + 1, nextAncestors),
    ];
  });
}

export function renderToc(container, items) {
  if (!container) return;

  const tocMarkup = items
    .map((item) => {
      const marginLeft = 25 * item.level;
      const safeLabel = escapeHtml(item.label || "");
      const safeHref = escapeHtml(item.href || "");

      return `
        <div class="slide-contents-item">
          <button type="button" class="slide-contents-item-label" style="margin-left: ${marginLeft}px" title="${escapeHtml(
            item.label || "",
          )}" data-href="${safeHref}" aria-label="${safeLabel}" aria-current="false">${safeLabel}</button>
          <span class="slide-contents-item-page"></span>
        </div>
      `;
    })
    .join("");

  container.innerHTML = tocMarkup;
}

export function renderTocTree(container, items) {
  if (!container) return;
  container.innerHTML = _buildTreeHtml(items, 0);
}

function _buildTreeHtml(items, level) {
  if (!Array.isArray(items) || !items.length) return "";

  return items
    .map((item) => {
      const hasChildren =
        Array.isArray(item.subitems) && item.subitems.length > 0;
      const safeLabel = escapeHtml(item.label || "");
      const safeHref = escapeHtml(item.href || "");
      const paddingLeft = 16 + 20 * level;

      const toggleHtml = hasChildren
        ? `<button type="button" class="toc-toggle" aria-expanded="false" aria-label="${safeLabel}" tabindex="-1">&#9654;</button>`
        : `<span class="toc-toggle-spacer" aria-hidden="true"></span>`;

      const rowHtml = `<div class="slide-contents-item" style="padding-left:${paddingLeft}px">${toggleHtml}<button type="button" class="slide-contents-item-label" title="${safeLabel}" data-href="${safeHref}" aria-label="${safeLabel}" aria-current="false">${safeLabel}</button><span class="slide-contents-item-page"></span></div>`;

      if (hasChildren) {
        return `<div class="toc-node">${rowHtml}<div class="toc-children" hidden>${_buildTreeHtml(item.subitems, level + 1)}</div></div>`;
      }

      return rowHtml;
    })
    .join("");
}

export function syncSelectedTocItem(currentHref) {
  const tocRows = queryAll(".slide-contents-item");
  const normalizedCurrent = currentHref ? currentHref.split("#")[0] : "";

  tocRows.forEach((row) => {
    const label = row.querySelector(".slide-contents-item-label");
    if (!label) return;

    const itemHref = getItemHref(label).split("#")[0];
    const isSelected =
      !!normalizedCurrent &&
      !!itemHref &&
      (itemHref === normalizedCurrent ||
        normalizedCurrent.endsWith(`/${itemHref}`) ||
        itemHref.endsWith(`/${normalizedCurrent}`) ||
        normalizedCurrent.endsWith(itemHref));
    label.classList.toggle("selected", isSelected);
    label.setAttribute("aria-current", isSelected ? "true" : "false");

    if (isSelected) {
      // Auto-expand all ancestor .toc-children so the selected item is visible
      let el = label.parentElement; // .slide-contents-item
      while (el) {
        if (
          el.classList &&
          el.classList.contains("toc-children") &&
          el.hidden
        ) {
          el.hidden = false;
          const prevSibling = el.previousElementSibling;
          if (
            prevSibling &&
            prevSibling.classList.contains("slide-contents-item")
          ) {
            const toggle = prevSibling.querySelector(".toc-toggle");
            if (toggle) {
              toggle.setAttribute("aria-expanded", "true");
              toggle.innerHTML = "&#9660;";
            }
          }
        }
        el = el.parentElement;
      }
    }
  });
}

export function getItemHref(element) {
  if (!element) return "";
  return (
    element.getAttribute("data-href") || element.getAttribute("href") || ""
  );
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
