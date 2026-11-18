import { resolveAppUrl } from "../../../../../api/urls.js";

const HIGHLIGHT_COLORS = {
  green: { fill: "#a5d6a7", label: "Green" },
  yellow: { fill: "#ffeb3b", label: "Yellow" },
  blue: { fill: "#90caf9", label: "Blue" },
  pink: { fill: "#f48fb1", label: "Pink" },
  underline: { fill: "#f9a825", label: "Underline" },
};

const DEFAULT_HIGHLIGHT_COLOR = "green";

function readCookie(name) {
  const pattern = new RegExp(`(?:^|; )${name}=([^;]*)`);
  const match = document.cookie.match(pattern);
  return match ? decodeURIComponent(match[1]) : "";
}

function highlightStyles(color) {
  const fill =
    HIGHLIGHT_COLORS[color]?.fill ||
    HIGHLIGHT_COLORS[DEFAULT_HIGHLIGHT_COLOR].fill;
  // fill-opacity: 0.3 keeps text easily readable through the highlight.
  // The annotation SVG pane lives in the PARENT document; mix-blend-mode is
  // applied via an injected <style> in the parent document head.
  return { fill, "fill-opacity": "0.3" };
}

// Inject annotation CSS into the parent document exactly once.
// Must target parent doc because the marks-pane SVG is appended to the parent
// document, NOT inside the iframe.
function ensureParentAnnotationStyles() {
  const id = "epub-annotation-pane-styles";
  if (document.getElementById(id)) return;
  const css = [
    /* highlight rects — semi-transparent so text shows through */
    "g.epubjs-hl rect { fill-opacity: 0.35 !important; }",
    /* Light themes: multiply blends nicely with white/sepia backgrounds. */
    "body.theme-type-0 g.epubjs-hl, body.theme-type-1 g.epubjs-hl { mix-blend-mode: multiply; }",
    /* Night theme: multiply would erase the highlight on dark bg. Use screen
       blend mode so the colour lifts above the dark page. */
    "body.theme-type-2 g.epubjs-hl { mix-blend-mode: screen; }",
    "body.theme-type-2 g.epubjs-hl rect { fill-opacity: 0.55 !important; }",
    /* underlines — override hardcoded stroke on <line> children; force full opacity */
    "g.epub-underline line, g.epubjs-ul line { stroke: #e67e22 !important; stroke-width: 2.5px !important; stroke-linecap: round !important; stroke-opacity: 1 !important; }",
    /* underline hit-area rects must never render any border/fill */
    "g.epub-underline rect, g.epubjs-ul rect { fill: none !important; stroke: none !important; }",
    /* Quote annotation: rendered as an underline with a thin purple bottom line. */
    "g.epubjs-quote line { stroke: #c084fc !important; stroke-width: 1.5px !important; stroke-linecap: round !important; stroke-opacity: 1 !important; }",
    "g.epubjs-quote rect { fill: none !important; stroke: none !important; }",
    /* pointer cursor so users know annotations are clickable */
    "g.epubjs-hl, g.epub-underline, g.epubjs-ul, g.epubjs-quote { cursor: pointer; }",
  ].join("\n");
  const style = document.createElement("style");
  style.id = id;
  style.textContent = css;
  (document.head || document.documentElement).appendChild(style);
}

export const readerApplicationHighlightMethods = {
  initializeHighlightState() {
    this.highlights = new Map(); // id -> highlight payload
    this.appliedHighlightIds = new Set();
    this.appliedHighlightTypes = new Map(); // id -> "highlight" | "underline"
    this.highlightToolbarElement = null;
    this.pendingSelection = null;
    this._highlightContentsBound = new WeakSet();
  },

  seedHighlightsFromManifest(manifest) {
    if (!this.highlights) this.initializeHighlightState();
    const initial = Array.isArray(manifest?.highlights)
      ? manifest.highlights
      : [];
    this.highlights.clear();
    this.appliedHighlightIds.clear();
    for (const item of initial) {
      if (item?.id) this.highlights.set(item.id, item);
    }
  },

  attachHighlightEventHandlers(sessionId) {
    if (!this.rendition || typeof this.rendition.on !== "function") return;
    if (!this.highlights) this.initializeHighlightState();

    // Apply seeded highlights immediately so they appear as soon as the first
    // view is rendered (epub.js stores them and attaches to matching views).
    this.applyPendingHighlights();

    const reapply = () => {
      if (!this.isSessionActive(sessionId)) return;
      this.applyPendingHighlights();
    };

    this.rendition.on("rendered", reapply);
    this.rendition.on("displayed", reapply);
    this.rendition.on("relocated", () => {
      if (!this.isSessionActive(sessionId)) return;
      // Hide selection toolbar and annotation menu when the page changes.
      this.hideHighlightToolbar();
      this._dismissAnnotationMenu?.();
      this.applyPendingHighlights();
      // Update persistent bookmark button appearance for the current location.
      this._syncBookmarkNavButton();
    });

    // Wire up the persistent bookmark button in the reader nav bar.
    this._attachNavBookmarkButton(sessionId);

    // Per-contents listener — fires reliably inside the iframe.
    if (this.rendition.hooks?.content?.register) {
      this.rendition.hooks.content.register((contents) => {
        if (!this.isSessionActive(sessionId)) return;
        this.bindHighlightContents(contents);
        // Some content may render before listeners are attached — retry now.
        this.applyPendingHighlights();
      });
    }

    // Fallback: rendition-level forwarding.
    this.rendition.on("selected", (cfiRange, contents) => {
      if (!this.isSessionActive(sessionId)) return;
      this.handleReaderTextSelected(cfiRange, contents);
    });
  },

  bindHighlightContents(contents) {
    if (!contents || this._highlightContentsBound?.has(contents)) return;
    this._highlightContentsBound.add(contents);

    const win = contents.window;
    const doc = contents.document;
    if (!win || !doc) return;

    // Inject annotation styles into the PARENT document — the marks-pane SVG
    // is appended to the parent doc container, not inside the iframe, so CSS
    // inside the iframe has no effect on highlight/underline rendering.
    try {
      ensureParentAnnotationStyles();
    } catch {
      // best effort
    }

    // Inject text-selection feedback CSS into the iframe document.
    try {
      const selStyleId = "epub-selection-styles";
      if (!doc.getElementById(selStyleId)) {
        const style = doc.createElement("style");
        style.id = selStyleId;
        style.textContent = [
          "::selection { background: rgba(255,235,59,0.45); }",
          ".epubjs-quote-text { font-style: italic; }",
          ".epubjs-quote-mark { font-style: normal; color: #7c3aed; font-weight: 600; }",
        ].join("\n");
        (doc.head || doc.documentElement).appendChild(style);
      }
    } catch {
      // best effort
    }

    const handleMouseUp = () => {
      try {
        const selection = win.getSelection?.();
        if (!selection || selection.isCollapsed) return;
        const text = selection.toString().trim();
        if (!text) return;
        const range = selection.getRangeAt(0);
        const cfiRange = contents.cfiFromRange?.(range);
        if (!cfiRange) return;
        this.handleReaderTextSelected(cfiRange, contents, text, range);
      } catch (error) {
        // best effort
      }
    };

    doc.addEventListener("mouseup", handleMouseUp);
    doc.addEventListener("touchend", handleMouseUp);

    // Hide the toolbar only when a brand-new selection starts (no active selection yet).
    doc.addEventListener("mousedown", () => {
      try {
        const selection = win.getSelection?.();
        if (!selection || selection.isCollapsed) {
          this.hideHighlightToolbar();
        }
      } catch {
        this.hideHighlightToolbar();
      }
    });
  },

  applyPendingHighlights() {
    if (!this.rendition?.annotations || !this.highlights) return;
    for (const highlight of this.highlights.values()) {
      if (!highlight?.cfi_range) continue;
      if (this.appliedHighlightIds.has(highlight.id)) continue;
      try {
        if (highlight.kind === "quote") {
          // Quotes render as a thin purple underline (not a tinted box) so the
          // quoted text reads cleanly with just a bottom rule beneath it.
          this.rendition.annotations.underline(
            highlight.cfi_range,
            { id: highlight.id, color: "quote" },
            (event) => this.showAnnotationMenu(highlight.id, event),
            "epubjs-quote",
            {},
          );
          this.appliedHighlightIds.add(highlight.id);
          this.appliedHighlightTypes?.set(highlight.id, "underline");
          continue;
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.warn("Failed to attach quote annotation", highlight.id, error);
        continue;
      }
      try {
        const isUnderline = highlight.color === "underline";
        if (isUnderline) {
          // Use epub.js underline API — draws SVG <line> elements under text.
          // Stroke color/width is controlled by CSS injected in parent doc.
          this.rendition.annotations.underline(
            highlight.cfi_range,
            { id: highlight.id },
            (event) => this.showAnnotationMenu(highlight.id, event),
            "epub-underline",
            {},
          );
        } else {
          // className MUST be a single token — epub.js calls classList.add(className)
          // which throws DOMException if the string contains spaces.
          this.rendition.annotations.highlight(
            highlight.cfi_range,
            { id: highlight.id, color: highlight.color },
            (event) => this.showAnnotationMenu(highlight.id, event),
            "epubjs-hl",
            highlightStyles(highlight.color),
          );
        }
        // epub.js stores the annotation and re-attaches it whenever the matching
        // section is rendered, so calling .add() once is sufficient.
        this.appliedHighlightIds.add(highlight.id);
        this.appliedHighlightTypes?.set(
          highlight.id,
          isUnderline ? "underline" : "highlight",
        );
      } catch (error) {
        // The annotation may be re-attempted on the next render event.
        // eslint-disable-next-line no-console
        console.warn(
          "Failed to attach highlight annotation",
          highlight.id,
          error,
        );
      }
    }
    // After underline SVGs are attached, mutate the iframe DOM so quoted text
    // is wrapped in italic and flanked by smart quotation marks. Idempotent
    // per (iframe, highlight id).
    try {
      this._applyQuoteDecorations();
    } catch {
      // best effort
    }
  },

  removeHighlightAnnotation(highlight) {
    if (!highlight?.cfi_range || !this.rendition?.annotations) return;
    const type =
      this.appliedHighlightTypes?.get(highlight.id) ||
      (highlight.color === "underline" ? "underline" : "highlight");
    try {
      this.rendition.annotations.remove(highlight.cfi_range, type);
    } catch {
      // ignore
    }
    if (highlight.kind === "quote") {
      this._undoQuoteDecoration(highlight.id);
    }
    this.appliedHighlightIds?.delete(highlight.id);
    this.appliedHighlightTypes?.delete(highlight.id);
  },

  _applyQuoteDecorations() {
    if (!this.rendition || !this.highlights) return;
    let contentsList = [];
    try {
      contentsList = this.rendition.getContents?.() || [];
    } catch {
      contentsList = [];
    }
    if (!Array.isArray(contentsList) || !contentsList.length) return;
    for (const highlight of this.highlights.values()) {
      if (highlight.kind !== "quote" || !highlight.cfi_range) continue;
      for (const contents of contentsList) {
        const doc = contents?.document;
        if (!doc) continue;
        // Already decorated in this iframe?
        if (doc.querySelector?.(`[data-quote-id="${highlight.id}"]`)) continue;
        let range;
        try {
          range = contents.range?.(highlight.cfi_range);
        } catch {
          range = null;
        }
        if (!range) continue;
        try {
          const frag = range.extractContents();
          const wrap = doc.createElement("span");
          wrap.className = "epubjs-quote-text";
          wrap.setAttribute("data-quote-id", highlight.id);
          wrap.appendChild(frag);

          const open = doc.createElement("span");
          open.className = "epubjs-quote-mark";
          open.setAttribute("data-quote-id", highlight.id);
          open.setAttribute("data-quote-role", "open");
          open.textContent = "\u201C";

          const close = doc.createElement("span");
          close.className = "epubjs-quote-mark";
          close.setAttribute("data-quote-id", highlight.id);
          close.setAttribute("data-quote-role", "close");
          close.textContent = "\u201D";

          range.insertNode(wrap);
          wrap.parentNode.insertBefore(open, wrap);
          if (wrap.nextSibling) {
            wrap.parentNode.insertBefore(close, wrap.nextSibling);
          } else {
            wrap.parentNode.appendChild(close);
          }
        } catch (error) {
          // Range may cross element boundaries; skip decoration silently.
          // The underline still renders the bottom rule.
          // eslint-disable-next-line no-console
          console.debug("Quote decoration skipped", highlight.id, error);
        }
      }
    }
  },

  _undoQuoteDecoration(id) {
    if (!this.rendition || !id) return;
    let contentsList = [];
    try {
      contentsList = this.rendition.getContents?.() || [];
    } catch {
      contentsList = [];
    }
    for (const contents of contentsList) {
      const doc = contents?.document;
      if (!doc?.querySelectorAll) continue;
      const nodes = doc.querySelectorAll(`[data-quote-id="${id}"]`);
      nodes.forEach((node) => {
        if (node.classList.contains("epubjs-quote-text")) {
          // Unwrap: move children out, then remove the wrapper.
          const parent = node.parentNode;
          if (!parent) {
            node.remove();
            return;
          }
          while (node.firstChild) parent.insertBefore(node.firstChild, node);
          node.remove();
        } else {
          // Quote-mark spans — just remove.
          node.remove();
        }
      });
    }
  },

  ensureHighlightToolbar() {
    if (
      this.highlightToolbarElement &&
      this.highlightToolbarElement.isConnected
    ) {
      return this.highlightToolbarElement;
    }
    const toolbar = document.createElement("div");
    toolbar.className = "reader-highlight-toolbar";
    toolbar.setAttribute("role", "toolbar");
    toolbar.setAttribute("aria-label", "Highlight selection");
    toolbar.style.cssText = [
      "position:absolute",
      "z-index:99999",
      "display:none",
      "align-items:center",
      "gap:6px",
      "padding:6px 8px",
      "background:#1f2937",
      "color:#fff",
      "border-radius:8px",
      "box-shadow:0 6px 18px rgba(0,0,0,.35)",
      "font:500 12px/1 system-ui,-apple-system,Segoe UI,sans-serif",
      "user-select:none",
      "-webkit-user-select:none",
    ].join(";");

    // CRITICAL: prevent the toolbar from stealing focus and collapsing the
    // iframe's selection. mousedown is the event that clears selection — we
    // must preventDefault BEFORE it propagates.
    toolbar.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });
    toolbar.addEventListener(
      "touchstart",
      (event) => {
        event.preventDefault();
      },
      { passive: false },
    );

    for (const color of Object.keys(HIGHLIGHT_COLORS)) {
      const meta = HIGHLIGHT_COLORS[color];
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.color = color;
      const title =
        color === "underline"
          ? "Add note (underline)"
          : `Add note (${meta.label.toLowerCase()})`;
      button.title = title;
      button.setAttribute("aria-label", title);
      const swatch =
        color === "underline"
          ? "background:#374151;background-image:linear-gradient(to bottom,transparent 60%,#f9a825 62%,#f9a825 78%,transparent 80%)"
          : `background:${meta.fill}`;
      button.style.cssText = [
        "width:24px",
        "height:24px",
        "border-radius:50%",
        "border:2px solid rgba(255,255,255,.7)",
        "cursor:pointer",
        "padding:0",
        "transition:transform .08s ease",
        swatch,
      ].join(";");
      button.addEventListener("mouseenter", () => {
        button.style.transform = "scale(1.12)";
      });
      button.addEventListener("mouseleave", () => {
        button.style.transform = "scale(1)";
      });
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        this.createHighlightFromSelection(color);
      });
      toolbar.appendChild(button);
    }

    const makeIconButton = (label, title, onClick) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.title = title;
      btn.setAttribute("aria-label", title);
      btn.textContent = label;
      btn.style.cssText = [
        "background:transparent",
        "border:1px solid rgba(255,255,255,.25)",
        "border-radius:4px",
        "color:#fff",
        "cursor:pointer",
        "font-size:14px",
        "line-height:1",
        "padding:4px 6px",
        "min-width:28px",
      ].join(";");
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        onClick();
      });
      return btn;
    };

    toolbar.appendChild(
      makeIconButton("💬", "Note with comment", () =>
        this.createHighlightFromSelection(DEFAULT_HIGHLIGHT_COLOR, {
          withNote: true,
        }),
      ),
    );
    toolbar.appendChild(
      makeIconButton("❝", "Save as quote", () =>
        this.createQuoteFromSelection(),
      ),
    );
    toolbar.appendChild(
      makeIconButton("⧉", "Copy selection", () => this.copyPendingSelection()),
    );

    // Separator line
    const sep = document.createElement("div");
    sep.style.cssText =
      "width:1px;height:20px;background:rgba(255,255,255,.25);margin:0 2px;";
    toolbar.appendChild(sep);

    toolbar.appendChild(
      makeIconButton("🔖", "Bookmark current page", () => {
        this.createBookmarkAtCurrentLocation();
        this.hideHighlightToolbar();
      }),
    );

    document.body.appendChild(toolbar);
    this.highlightToolbarElement = toolbar;

    // Global dismiss when clicking outside (in parent doc only).
    if (!this._highlightToolbarDismissBound) {
      const dismiss = (event) => {
        if (event.target.closest?.(".reader-highlight-toolbar")) return;
        this.hideHighlightToolbar();
      };
      document.addEventListener("mousedown", dismiss);
      this._highlightToolbarDismissBound = true;
    }

    return toolbar;
  },

  hideHighlightToolbar() {
    if (this.highlightToolbarElement) {
      this.highlightToolbarElement.style.display = "none";
    }
  },

  // Show a brief ✓ message inside the toolbar, then hide it automatically.
  // Preserves all event listeners (hides/shows children rather than replacing HTML).
  showToolbarFeedback(message) {
    const toolbar = this.highlightToolbarElement;
    if (!toolbar) return;
    // Hide action buttons temporarily
    const buttons = Array.from(toolbar.children);
    buttons.forEach((b) => (b.style.display = "none"));
    const badge = document.createElement("span");
    badge.textContent = `✓ ${message}`;
    badge.style.cssText = [
      "color:#4ade80",
      "font-weight:600",
      "font-size:13px",
      "padding:0 8px",
      "letter-spacing:.01em",
    ].join(";");
    toolbar.appendChild(badge);
    setTimeout(() => {
      try {
        toolbar.removeChild(badge);
      } catch {
        // already removed
      }
      buttons.forEach((b) => (b.style.display = ""));
      this.hideHighlightToolbar();
    }, 1400);
  },

  handleReaderTextSelected(cfiRange, contents, providedText, providedRange) {
    if (!cfiRange) return;
    let selectedText = providedText || "";
    let rect = null;
    try {
      const win = contents?.window;
      const selection = win?.getSelection?.();
      if (!selectedText && selection) {
        selectedText = selection.toString();
      }
      const range =
        providedRange ||
        (selection && selection.rangeCount > 0
          ? selection.getRangeAt(0)
          : null);
      if (range) rect = range.getBoundingClientRect();
    } catch {
      // ignore
    }
    selectedText = (selectedText || "").trim();
    if (!selectedText) {
      this.hideHighlightToolbar();
      return;
    }

    const currentLocation = this.book?.rendition?.currentLocation?.();
    const chapterHref = currentLocation?.start?.href || this.currentHref || "";

    this.pendingSelection = {
      cfiRange,
      text: selectedText.slice(0, 5000),
      chapterHref,
      chapterLabel: this.lookupChapterLabel(chapterHref),
    };

    this.showHighlightToolbarForSelection(contents, rect);
  },

  lookupChapterLabel(href) {
    if (!href) return "";
    const items = this.flattenedToc || [];
    const match = items.find(
      (entry) => entry.href && href.endsWith(entry.href.split("#")[0]),
    );
    return match?.label || "";
  },

  showHighlightToolbarForSelection(contents, providedRect) {
    const toolbar = this.ensureHighlightToolbar();
    let rect = providedRect || null;
    if (!rect) {
      try {
        const selection = contents?.window?.getSelection?.();
        if (selection && selection.rangeCount > 0) {
          rect = selection.getRangeAt(0).getBoundingClientRect();
        }
      } catch {
        rect = null;
      }
    }

    const iframe =
      contents?.iframe || contents?.document?.defaultView?.frameElement;
    const iframeRect = iframe?.getBoundingClientRect?.() || {
      left: 0,
      top: 0,
      width: 0,
    };

    toolbar.style.display = "inline-flex";
    // Use rAF to allow the browser to layout the toolbar so we can read width.
    requestAnimationFrame(() => {
      const toolbarWidth = toolbar.offsetWidth || 220;
      const toolbarHeight = toolbar.offsetHeight || 40;

      let top;
      let left;
      if (rect) {
        const selCenterX = rect.left + rect.width / 2 + iframeRect.left;
        top = rect.top + iframeRect.top - toolbarHeight - 10 + window.scrollY;
        left = selCenterX - toolbarWidth / 2 + window.scrollX;
        if (top < window.scrollY + 8) {
          // Not enough room above — place below the selection.
          top = rect.bottom + iframeRect.top + 10 + window.scrollY;
        }
      } else {
        top = window.scrollY + 80;
        left = window.scrollX + 80;
      }

      const maxLeft =
        window.scrollX +
        document.documentElement.clientWidth -
        toolbarWidth -
        8;
      toolbar.style.top = `${Math.max(window.scrollY + 8, top)}px`;
      toolbar.style.left = `${Math.min(Math.max(window.scrollX + 8, left), maxLeft)}px`;
    });
  },

  copyPendingSelection() {
    const text = this.pendingSelection?.text || "";
    if (!text) return;
    const finalize = () => {
      this.hideHighlightToolbar();
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .catch(() => this._fallbackCopy(text))
        .finally(finalize);
      return;
    }
    this._fallbackCopy(text);
    finalize();
  },

  _fallbackCopy(text) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.top = "-1000px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    } catch {
      // best effort
    }
  },

  // Promise-based centered modal for note input (replaces window.prompt).
  // Returns { note, color } when saved, or null if user cancelled.
  // If `showColorPicker` is true, displays color swatches above the textarea.
  _showNoteInputModal(existingNote = "", options = {}) {
    const { showColorPicker = false, initialColor = DEFAULT_HIGHLIGHT_COLOR } =
      options;
    return new Promise((resolve) => {
      const isDark =
        document.documentElement.classList.contains("dark") ||
        window.matchMedia?.("(prefers-color-scheme: dark)").matches;

      const overlay = document.createElement("div");
      overlay.style.cssText = [
        "position:fixed",
        "inset:0",
        "z-index:999999",
        "background:rgba(0,0,0,0.5)",
        "display:flex",
        "align-items:center",
        "justify-content:center",
        "padding:16px",
      ].join(";");

      const card = document.createElement("div");
      card.style.cssText = [
        isDark
          ? "background:#1f2937;color:#f9fafb;border:1px solid #374151"
          : "background:#fff;color:#111827;border:1px solid #e5e7eb",
        "border-radius:12px",
        "box-shadow:0 20px 60px rgba(0,0,0,.4)",
        "padding:24px",
        "width:100%",
        "max-width:440px",
        "display:flex",
        "flex-direction:column",
        "gap:12px",
        "font:500 14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif",
      ].join(";");

      const title = document.createElement("h2");
      title.textContent = "Add a comment";
      title.style.cssText = "margin:0;font-size:16px;font-weight:600;";
      card.appendChild(title);

      let selectedColor = initialColor;
      if (showColorPicker) {
        const colorRow = document.createElement("div");
        colorRow.style.cssText =
          "display:flex;gap:8px;align-items:center;padding:2px 0;";
        const colorLabel = document.createElement("span");
        colorLabel.textContent = "Color:";
        colorLabel.style.cssText = "font-size:12px;opacity:0.7;";
        colorRow.appendChild(colorLabel);
        const dotButtons = [];
        for (const [color, meta] of Object.entries(HIGHLIGHT_COLORS)) {
          if (color === "underline") continue;
          const dot = document.createElement("button");
          dot.type = "button";
          dot.title = meta.label;
          dot.dataset.color = color;
          const applyStyle = () => {
            dot.style.cssText = [
              "width:22px;height:22px;border-radius:50%;cursor:pointer;padding:0;transition:transform .1s",
              `background:${meta.fill}`,
              selectedColor === color
                ? "border:2px solid #6366f1;box-shadow:0 0 0 2px rgba(99,102,241,.3);transform:scale(1.1)"
                : "border:2px solid rgba(0,0,0,.15)",
            ].join(";");
          };
          applyStyle();
          dot.addEventListener("click", () => {
            selectedColor = color;
            dotButtons.forEach((b) => b._refresh());
          });
          dot._refresh = applyStyle;
          dotButtons.push(dot);
          colorRow.appendChild(dot);
        }
        card.appendChild(colorRow);
      }

      const ta = document.createElement("textarea");
      ta.value = existingNote;
      ta.placeholder = "Write your comment\u2026";
      ta.rows = 4;
      ta.style.cssText = [
        "width:100%",
        "box-sizing:border-box",
        isDark
          ? "background:#374151;color:#f9fafb;border:1px solid #4b5563"
          : "background:#f9fafb;color:#111827;border:1px solid #d1d5db",
        "border-radius:8px",
        "padding:8px 10px",
        "font:inherit",
        "font-size:13px",
        "line-height:1.5",
        "resize:vertical",
        "outline:none",
      ].join(";");
      card.appendChild(ta);

      const hint = document.createElement("p");
      hint.textContent = "Ctrl+Enter to save \u00b7 Esc to cancel";
      hint.style.cssText = "margin:0;font-size:11px;opacity:0.55;";
      card.appendChild(hint);

      const footer = document.createElement("div");
      footer.style.cssText = "display:flex;justify-content:flex-end;gap:8px;";

      const btnBase = [
        "border:0",
        "border-radius:8px",
        "padding:7px 18px",
        "font:inherit",
        "font-size:13px",
        "font-weight:500",
        "cursor:pointer",
        "transition:opacity 0.1s",
      ].join(";");

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.textContent = "Cancel";
      cancelBtn.style.cssText =
        btnBase +
        ";" +
        (isDark
          ? "background:#374151;color:#d1d5db;"
          : "background:#f3f4f6;color:#374151;");

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.textContent = "Save";
      saveBtn.style.cssText = btnBase + ";background:#6366f1;color:#fff;";

      footer.appendChild(cancelBtn);
      footer.appendChild(saveBtn);
      card.appendChild(footer);
      overlay.appendChild(card);
      document.body.appendChild(overlay);

      const close = (value) => {
        document.body.removeChild(overlay);
        resolve(value);
      };
      const submit = () => {
        const note = ta.value.trim();
        close(showColorPicker ? { note, color: selectedColor } : note);
      };

      ta.focus();

      cancelBtn.addEventListener("click", () => close(null));
      saveBtn.addEventListener("click", submit);
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close(null);
      });
      ta.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          close(null);
        }
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
      });
    });
  },

  async createHighlightFromSelection(color, { withNote = false } = {}) {
    return this._persistSelection({ kind: "highlight", color, withNote });
  },

  async createQuoteFromSelection({ withNote = false } = {}) {
    return this._persistSelection({ kind: "quote", color: "yellow", withNote });
  },

  async _persistSelection({ kind, color, withNote }) {
    // Guard against rapid double-clicks / multiple colour taps from the
    // selection toolbar: claim the pending selection atomically so a second
    // concurrent call sees `null` and bails out.
    const pending = this.pendingSelection;
    if (!pending) return;
    if (this._persistInFlight) return;
    this._persistInFlight = true;
    this.pendingSelection = null;
    const highlightsUrl = resolveAppUrl(this.launchManifest?.highlights_url);
    if (!highlightsUrl) {
      console.warn("Highlights are unavailable for this reader session.");
      this._persistInFlight = false;
      return;
    }

    // Prevent duplicate: update existing highlight when the new selection
    // refers to the same span. We match on exact CFI OR identical text within
    // the same chapter (covers cases where re-selecting the same words yields
    // a slightly different CFI).
    const sameSpan = (existing) => {
      if (!existing || existing.kind !== kind) return false;
      if (existing.cfi_range === pending.cfiRange) return true;
      const a = (existing.text || "").trim();
      const b = (pending.text || "").trim();
      if (!a || !b) return false;
      const sameChapter =
        !pending.chapterHref ||
        !existing.chapter_href ||
        existing.chapter_href === pending.chapterHref;
      return sameChapter && a === b;
    };
    if (this.highlights) {
      for (const [id, existing] of this.highlights) {
        if (!sameSpan(existing)) continue;
        if (existing.color !== color) {
          try {
            const csrfToken = readCookie("csrftoken");
            const patchUrl = resolveAppUrl(
              this.launchManifest?.highlights_url?.replace(/\/?$/, "/") +
                id +
                "/",
            );
            const res = await fetch(patchUrl, {
              method: "PATCH",
              credentials: "include",
              headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
                ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
              },
              body: JSON.stringify({ color }),
            });
            if (res.ok) {
              const updated = await res.json();
              this.removeHighlightAnnotation(existing);
              this.highlights.set(id, updated);
              this.applyPendingHighlights();
            }
          } catch {
            /* best effort */
          }
        }
        this.showToolbarFeedback("Color updated");
        this._persistInFlight = false;
        return;
      }
    }

    let note = "";
    let chosenColor = color;
    if (withNote) {
      const result = await this._showNoteInputModal("", {
        showColorPicker: kind === "highlight",
        initialColor: color,
      });
      if (result === null) {
        this._persistInFlight = false;
        return;
      } // user cancelled
      if (typeof result === "string") {
        note = result;
      } else {
        note = result.note || "";
        chosenColor = result.color || color;
      }
    }

    const payload = {
      cfi_range: pending.cfiRange,
      text: pending.text,
      chapter_href: pending.chapterHref || "",
      chapter_label: pending.chapterLabel || "",
      color: chosenColor,
      kind,
      note,
    };

    const csrfToken = readCookie("csrftoken");
    try {
      const response = await fetch(highlightsUrl, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(
          `Failed to save highlight (${response.status}): ${detail}`,
        );
      }
      const saved = await response.json();
      if (!this.highlights) this.initializeHighlightState();
      this.highlights.set(saved.id, saved);
      this.applyPendingHighlights();
      // Show brief confirmation in toolbar so the user knows the action worked.
      const msg = saved.kind === "quote" ? "Quote saved" : "Saved";
      this.showToolbarFeedback(msg);
    } catch (error) {
      console.error("Failed to create highlight.", error);
      window.alert?.("Could not save selection. Please try again.");
      this.hideHighlightToolbar();
    } finally {
      this._persistInFlight = false;
      try {
        this.rendition
          ?.getContents?.()
          .forEach?.((c) => c?.window?.getSelection?.()?.removeAllRanges?.());
      } catch {
        // best effort
      }
    }
  },

  // ── Annotation click menu ────────────────────────────────────────────────

  showAnnotationMenu(id, event) {
    const highlight = this.highlights?.get(id);
    if (!highlight) return;

    this._dismissAnnotationMenu();

    const menu = document.createElement("div");
    menu.className = "reader-annotation-menu";
    menu.style.cssText = [
      "position:fixed",
      "z-index:99998",
      "padding:6px",
      "background:#1f2937",
      "color:#f9fafb",
      "border-radius:8px",
      "box-shadow:0 6px 18px rgba(0,0,0,.4)",
      "display:inline-flex",
      "align-items:center",
      "gap:6px",
      "font:500 12px/1 system-ui,-apple-system,Segoe UI,sans-serif",
      "left:-9999px",
      "top:-9999px",
      "width:170px",
    ].join(";");

    // Colour changes are handled exclusively by the selection toolbar
    // (re-select the same text and pick a new colour). The annotation menu
    // shown when clicking an existing highlight only offers Edit + Delete.

    // Edit note — inline textarea (no dialog)
    menu.appendChild(
      this._annotationMenuBtn("✏️ Edit", () => {
        const existing = this.highlights.get(id);
        menu.innerHTML = "";
        menu.style.flexDirection = "column";
        menu.style.alignItems = "stretch";
        menu.style.padding = "8px";
        menu.style.minWidth = "220px";
        const ta = document.createElement("textarea");
        ta.value = existing?.note || "";
        ta.rows = 3;
        ta.placeholder = "Add a note…";
        ta.style.cssText =
          "width:100%;box-sizing:border-box;padding:6px 8px;background:rgba(255,255,255,.1);color:#f9fafb;border:1px solid rgba(255,255,255,.2);border-radius:6px;font:13px/1.4 inherit;resize:vertical;outline:none;";
        menu.appendChild(ta);
        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.textContent = "Save";
        saveBtn.style.cssText =
          "margin-top:6px;width:100%;padding:6px 10px;background:#3b82f6;color:#fff;border:0;border-radius:6px;cursor:pointer;font:500 12px inherit;";
        saveBtn.addEventListener("click", () => {
          this.updateHighlightById(id, { note: ta.value });
          this._dismissAnnotationMenu();
        });
        menu.appendChild(saveBtn);
        requestAnimationFrame(() => ta.focus());
      }),
    );

    // Delete button
    menu.appendChild(
      this._annotationMenuBtn(
        "🗑 Delete",
        () => {
          this.deleteHighlightById(id);
          this._dismissAnnotationMenu();
        },
        "#f87171",
      ),
    );

    menu.addEventListener("mousedown", (e) => e.stopPropagation());
    document.body.appendChild(menu);
    this._annotationMenuElement = menu;

    // Position just below the actual highlighted text. Prefer the bounding
    // rect of the clicked SVG element (highlight rect) over the click coords.
    requestAnimationFrame(() => {
      const mw = menu.offsetWidth || 160;
      const mh = menu.offsetHeight || 36;
      let anchorRect = null;
      try {
        const target = event?.target;
        if (target && typeof target.getBoundingClientRect === "function") {
          // Walk up to the annotation <g> so we get the full highlight span.
          const g =
            target.closest?.("g.epubjs-hl, g.epub-underline, g.epubjs-ul") ||
            target;
          const r = g.getBoundingClientRect?.();
          if (r && (r.width > 0 || r.height > 0)) anchorRect = r;
        }
      } catch {
        anchorRect = null;
      }

      let top;
      let left;
      if (anchorRect) {
        const centerX = anchorRect.left + anchorRect.width / 2;
        left = centerX - mw / 2;
        top = anchorRect.bottom + 6;
        // Flip above if no room below.
        if (top + mh + 8 > window.innerHeight) {
          top = anchorRect.top - mh - 6;
        }
      } else {
        const cx = event?.clientX ?? 80;
        const cy = event?.clientY ?? 80;
        left = cx - mw / 2;
        top = cy + 10;
      }
      menu.style.left = `${Math.min(Math.max(8, left), window.innerWidth - mw - 8)}px`;
      menu.style.top = `${Math.min(Math.max(8, top), window.innerHeight - mh - 8)}px`;
    });

    // Dismiss on outside click — listen on the parent document AND on every
    // rendered EPUB iframe document, because clicks inside the iframe do not
    // bubble to the parent, and the menu itself lives in the parent DOM (so
    // any iframe click is, by definition, outside the menu).
    const cleanupListeners = [];
    const handleOutside = (e) => {
      // Parent-doc clicks: only dismiss if the click target is outside the menu.
      // Iframe clicks: always outside the menu, so always dismiss.
      const target = e?.target;
      const insideMenu =
        target && typeof menu.contains === "function" && menu.contains(target);
      if (insideMenu) return;
      this._dismissAnnotationMenu();
      cleanupListeners.forEach((fn) => {
        try {
          fn();
        } catch {
          // best effort
        }
      });
    };

    const attachOutside = () => {
      document.addEventListener("mousedown", handleOutside);
      cleanupListeners.push(() =>
        document.removeEventListener("mousedown", handleOutside),
      );
      try {
        const contentsList = this.rendition?.getContents?.() || [];
        for (const contents of contentsList) {
          const doc = contents?.document;
          if (!doc?.addEventListener) continue;
          doc.addEventListener("mousedown", handleOutside);
          doc.addEventListener("touchstart", handleOutside);
          cleanupListeners.push(() => {
            try {
              doc.removeEventListener("mousedown", handleOutside);
              doc.removeEventListener("touchstart", handleOutside);
            } catch {
              // best effort
            }
          });
        }
      } catch {
        // best effort
      }
    };
    setTimeout(attachOutside, 0);
    this._annotationMenuCleanup = () => {
      cleanupListeners.forEach((fn) => {
        try {
          fn();
        } catch {
          // best effort
        }
      });
      cleanupListeners.length = 0;
    };
  },

  _dismissAnnotationMenu() {
    if (this._annotationMenuElement?.parentNode) {
      this._annotationMenuElement.parentNode.removeChild(
        this._annotationMenuElement,
      );
    }
    this._annotationMenuElement = null;
    if (typeof this._annotationMenuCleanup === "function") {
      try {
        this._annotationMenuCleanup();
      } catch {
        // best effort
      }
      this._annotationMenuCleanup = null;
    }
  },

  _annotationMenuBtn(label, onClick, color = "#f3f4f6") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.style.cssText = [
      "display:block;width:100%;background:transparent;border:0;",
      "padding:7px 10px;text-align:left;cursor:pointer;border-radius:6px;",
      "font:inherit;font-size:12px;transition:background .1s;",
      `color:${color}`,
    ].join("");
    btn.addEventListener("mouseenter", () => {
      btn.style.background = "rgba(255,255,255,.1)";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.background = "transparent";
    });
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      onClick();
    });
    return btn;
  },

  // ── Persistent nav-bar bookmark button ──────────────────────────────────

  _attachNavBookmarkButton(sessionId) {
    const btn = document.getElementById("reader-bookmark-btn");
    if (!btn || btn._bookmarkHandlerAttached) return;
    btn._bookmarkHandlerAttached = true;
    btn.addEventListener("click", () => {
      if (!this.isSessionActive(sessionId)) return;
      this.createBookmarkAtCurrentLocation();
    });
  },

  // Tint the nav bookmark button when the current location already has a
  // saved bookmark (best-effort: checks in-memory bookmarks list).
  _syncBookmarkNavButton() {
    const btn = document.getElementById("reader-bookmark-btn");
    if (!btn) return;
    const location = this.rendition?.currentLocation?.();
    const cfi = location?.start?.cfi || "";
    const alreadyBookmarked =
      cfi &&
      this.bookmarks &&
      [...this.bookmarks.values()].some((b) => b.location === cfi);
    btn.style.color = alreadyBookmarked ? "#f59e0b" : "";
    btn.title = alreadyBookmarked
      ? "Page already bookmarked"
      : "Bookmark this page";
  },

  // ── Bookmark current reading position ───────────────────────────────────

  async createBookmarkAtCurrentLocation() {
    const bookmarksUrl = resolveAppUrl(this.launchManifest?.bookmarks_url);
    if (!bookmarksUrl) {
      console.warn("Bookmarks are unavailable for this reader session.");
      return;
    }
    const location = this.rendition?.currentLocation?.();
    const cfi = location?.start?.cfi || location?.cfi || "";
    if (!cfi) return;

    const chapterHref = location?.start?.href || this.currentHref || "";
    const chapterLabel = this.lookupChapterLabel(chapterHref);

    const payload = {
      location: cfi,
      chapter_href: chapterHref,
      chapter_label: chapterLabel || "",
      label: chapterLabel || "Bookmarked page",
    };

    const csrfToken = readCookie("csrftoken");
    try {
      const response = await fetch(bookmarksUrl, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to save bookmark (${response.status})`);
      }
      const saved = await response.json().catch(() => ({}));
      // Keep an in-memory record so the nav button can reflect saved state.
      if (!this.bookmarks) this.bookmarks = new Map();
      if (saved?.id) this.bookmarks.set(saved.id, saved);
      this._syncBookmarkNavButton();
      this.showToolbarFeedback("Bookmarked");
    } catch (error) {
      console.error("Failed to create bookmark.", error);
      window.alert?.("Could not save bookmark. Please try again.");
    }
  },

  _detailUrlFor(id) {
    const base = resolveAppUrl(this.launchManifest?.highlights_url);
    if (!base) return "";
    // The list URL ends with /highlights/ — append <uuid>/.
    return base.replace(/\/?$/, "/").replace(/\/+$/, "/") + `${id}/`;
  },

  async updateHighlightById(id, body) {
    const detailUrl = this._detailUrlFor(id);
    if (!detailUrl) return;
    const csrfToken = readCookie("csrftoken");
    try {
      const response = await fetch(detailUrl, {
        method: "PATCH",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify(body),
      });
      if (!response.ok)
        throw new Error(`Failed to update highlight (${response.status})`);
      const updated = await response.json();
      this.highlights.set(id, updated);
    } catch (error) {
      console.error("Failed to update highlight.", error);
    }
  },

  async deleteHighlightById(id) {
    const highlight = this.highlights?.get(id);
    if (!highlight) return;
    const detailUrl = this._detailUrlFor(id);
    if (!detailUrl) return;
    const csrfToken = readCookie("csrftoken");
    try {
      const response = await fetch(detailUrl, {
        method: "DELETE",
        credentials: "include",
        headers: {
          Accept: "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
      });
      if (!response.ok && response.status !== 204) {
        throw new Error(`Failed to delete highlight (${response.status})`);
      }
      this.removeHighlightAnnotation(highlight);
      this.highlights.delete(id);
    } catch (error) {
      console.error("Failed to delete highlight.", error);
    }
  },
};
