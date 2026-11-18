const SKIPPABLE_TAGS = new Set([
  "script",
  "style",
  "link",
  "meta",
  "img",
  "video",
  "audio",
  "canvas",
  "source",
  "picture"
]);

export function createThemeColorApplicator({ doc, isDocumentUsable, themeTextColor }) {
  return function applyColorToElement(element) {
    if (!isDocumentUsable(doc) || !element || element.nodeType !== 1 || !element.isConnected) {
      return;
    }
    if (!element.style) return;

    const tagName = element.tagName ? element.tagName.toLowerCase() : "";
    if (SKIPPABLE_TAGS.has(tagName)) return;
    if (typeof element.closest === "function" && element.closest("a[href]")) {
      element.style.removeProperty("color");
      element.style.removeProperty("-webkit-text-fill-color");
      if (tagName === "text" || tagName === "tspan") {
        element.style.removeProperty("fill");
      }
      return;
    }

    element.style.setProperty("color", themeTextColor, "important");
    element.style.setProperty("-webkit-text-fill-color", themeTextColor, "important");

    if (tagName === "text" || tagName === "tspan") {
      element.style.setProperty("fill", themeTextColor, "important");
    }
  };
}

export function paintThemeTextColor({ applyColorToElement, body, doc, themeTextColor }) {
  const shouldRepaintAllElements = doc.__readerAppliedThemeColor !== themeTextColor;
  if (!shouldRepaintAllElements) return;

  applyColorToElement(body);
  body.querySelectorAll("*").forEach((element) => applyColorToElement(element));
}

export function installThemeMutationObserver({ applyColorToElement, body, doc, isDocumentUsable }) {
  const flushPendingNodes = () => {
    doc.__readerThemeObserverRaf = null;
    if (!isDocumentUsable(doc)) return;

    const pendingNodes = doc.__readerThemePendingNodes;
    if (!pendingNodes || !pendingNodes.size) return;

    pendingNodes.forEach((node) => {
      if (!node || node.nodeType !== 1 || !node.isConnected) return;

      applyColorToElement(node);
      if (node.querySelectorAll) {
        node.querySelectorAll("*").forEach((child) => applyColorToElement(child));
      }
    });

    pendingNodes.clear();
  };

  const queueNodeForThemeUpdate = (node) => {
    if (!node || node.nodeType !== 1 || !node.isConnected) return;

    if (!doc.__readerThemePendingNodes) {
      doc.__readerThemePendingNodes = new Set();
    }

    doc.__readerThemePendingNodes.add(node);

    if (doc.__readerThemeObserverRaf) return;
    doc.__readerThemeObserverRaf = requestAnimationFrame(flushPendingNodes);
  };

  const observer = new MutationObserver((mutations) => {
    if (!isDocumentUsable(doc)) return;

    mutations.forEach((mutation) => {
      if (mutation.type === "attributes") {
        queueNodeForThemeUpdate(mutation.target);
      }

      if (mutation.type === "childList") {
        mutation.addedNodes.forEach((node) => {
          queueNodeForThemeUpdate(node);
        });
      }
    });
  });

  observer.observe(body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["style", "class"]
  });

  doc.__readerThemeObserver = observer;
}
