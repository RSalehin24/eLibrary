const INTERNAL_LINK_CLEANUP_KEY = "__readerInternalLinkCleanup";
const EXTERNAL_PROTOCOL_PATTERN = /^[a-z][a-z0-9+.-]*:/i;

export function shouldIgnoreNavigableHref(href) {
  if (!href) return true;

  if (
    href.startsWith("//") ||
    href.startsWith("mailto:") ||
    href.startsWith("tel:") ||
    href.startsWith("data:") ||
    href.startsWith("javascript:") ||
    href.startsWith("blob:")
  ) {
    return true;
  }

  if (/^https?:\/\//i.test(href)) {
    return true;
  }

  if (EXTERNAL_PROTOCOL_PATTERN.test(href) && !href.startsWith("urn:epub:")) {
    return true;
  }

  return false;
}

export function attachInternalLinkInterceptor({
  controller,
  maxWait,
  onNavigate
}) {
  return controller.waitForDocument(maxWait).then((doc) => {
    if (!doc) return null;

    controller.detachInternalLinkInterceptor();

    const onClick = (event) => {
      const target =
        event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!target) return;

      const href = (target.getAttribute("href") || "").trim();
      if (shouldIgnoreNavigableHref(href)) {
        return;
      }

      event.preventDefault();
      onNavigate?.(href, target);
    };

    try {
      doc.addEventListener("click", onClick);
    } catch {
      return null;
    }

    doc[INTERNAL_LINK_CLEANUP_KEY] = () => {
      doc.removeEventListener("click", onClick);
    };
    controller.internalLinkCleanupDocument = doc;

    return doc;
  });
}

export function detachInternalLinkInterceptor({ controller }) {
  const doc = controller.internalLinkCleanupDocument || controller.getDocument();
  if (!doc) return;

  const cleanup = doc[INTERNAL_LINK_CLEANUP_KEY];
  if (typeof cleanup === "function") {
    try {
      cleanup();
    } catch {
      // Ignore iframe cleanup errors.
    }
    delete doc[INTERNAL_LINK_CLEANUP_KEY];
  }

  controller.internalLinkCleanupDocument = null;
}
