import {
  APP_THEME_COLOR,
  DEFAULT_THEME_INDEX,
  DEFAULT_FONT_SIZE,
  MIN_FONT_SIZE,
  MAX_FONT_SIZE,
  SELECTORS,
  STORAGE_KEYS,
  THEMES,
  VIEWPORT_FALLBACK_CONTENT,
} from ".././reader-settings.js";
import {
  addClass,
  delegateEvent,
  hasClass,
  hideElement,
  query,
  queryAll,
  removeClass,
  showElement,
  showElementFlex,
  toggleClass,
} from ".././utils/dom-helpers.js";
import {
  flattenToc,
  getItemHref,
  renderToc,
  syncSelectedTocItem,
} from ".././utils/toc-helpers.js";
import {
  bindDoubleTapToggle,
  createSwipeBinder,
} from ".././utils/gesture-handlers.js";
import { resolveAppUrl } from "../../../../../api/urls.js";
import { normalizeReaderManifestPayload } from "../../../../../features/reader/manifest.js";
import { LoadingIndicatorController } from ".././controllers/loading-indicator-controller.js";
import { ReaderThemeManager } from ".././controllers/theme-manager.js";
import { ShortcutDialogController } from ".././controllers/shortcut-dialog-controller.js";
import { IframeBridgeController } from ".././controllers/iframe-bridge-controller.js";
import { SettingsPanelController } from ".././controllers/settings-panel-controller.js";

const TOC_LABEL_SELECTOR = ".slide-contents-item-label";
const TOC_TOGGLE_EXCLUDED_TARGETS =
  "a, button, input, textarea, select, label, summary, [data-no-reader-toggle]";
const IFRAME_INTERACTION_READY_DELAY_MS = 200;
const IFRAME_INTERACTION_RELOCATED_DELAY_MS = 100;

function readCookie(name) {
  const pattern = new RegExp(`(?:^|; )${name}=([^;]*)`);
  const match = document.cookie.match(pattern);
  return match ? decodeURIComponent(match[1]) : "";
}

export const readerApplicationThemeViewportMethods = {
  handleTocSelection(event, target) {
    event.preventDefault();

    // If the clicked label belongs to a parent .toc-node whose children are
    // already expanded, treat the click as a collapse request. The first
    // click on a parent auto-expands via syncSelectedTocItem; without this,
    // there is no way to collapse it back from the label itself.
    const row = target.closest(".slide-contents-item");
    const node = row?.parentElement;
    if (node && node.classList && node.classList.contains("toc-node")) {
      const children = node.querySelector(":scope > .toc-children");
      if (children && !children.hidden) {
        children.hidden = true;
        const toggle = row.querySelector(".toc-toggle");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "false");
          toggle.innerHTML = "&#9654;";
        }
        return;
      }
    }

    const rawHref = getItemHref(target);
    const normalizedHref = this.normalizeHrefForComparison(rawHref);
    if (!normalizedHref) return;

    this.syncSectionWithHref(normalizedHref);
    this.display(rawHref, () => {
      this.refresh(rawHref);
    });
  },
  applyThemeByIndex(themeIndex) {
    const isApplied = this.readerThemeManager.applyThemeByIndex(
      themeIndex,
      this.rendition,
    );
    if (isApplied) {
      this.syncThemeControlState();
    }
    return isApplied;
  },
  cycleTheme() {
    const isApplied = this.readerThemeManager.cycleTheme(this.rendition);
    if (isApplied) {
      this.syncThemeControlState();
    }
    return isApplied;
  },
  changeFontSizeByStep(stepCount) {
    const hasChanged = this.readerThemeManager.changeFontSizeByStep(stepCount);
    this.syncFontControlState();
    return hasChanged;
  },
  closeSettings() {
    this.settingsPanelController.close();
  },
  syncThemeControlState() {
    const currentThemeIndex = this.readerThemeManager.getCurrentThemeIndex();

    queryAll(".bg-btn").forEach((button) => {
      const buttonThemeIndex = Number.parseInt(button?.dataset?.type || "", 10);
      const isActive =
        Number.isInteger(buttonThemeIndex) &&
        buttonThemeIndex === currentThemeIndex;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  },
  syncFontControlState() {
    const currentFontSize = this.readerThemeManager.getCurrentFontSize();
    const isAtMinimum = currentFontSize <= MIN_FONT_SIZE;
    const isAtMaximum = currentFontSize >= MAX_FONT_SIZE;

    queryAll(".size-btn").forEach((button) => {
      const tag = button?.dataset?.tag;
      const isDisabled =
        (tag === "small" && isAtMinimum) || (tag === "big" && isAtMaximum);
      button.disabled = isDisabled;
      button.setAttribute("aria-disabled", isDisabled ? "true" : "false");
    });
  },
  syncReaderControlStates() {
    this.syncThemeControlState();
    this.syncFontControlState();
  },
  syncChapterLabel(href) {
    if (!this.chapterLabelElement) return;
    const target = href || this.currentHref || "";
    const items = this.flattenedToc || [];
    const baseHref = target.split("#")[0];
    const matches = items.filter(
      (entry) => entry.href && baseHref.endsWith(entry.href.split("#")[0]),
    );
    // Prefer a leaf entry (no subitems) when multiple TOC nodes share the
    // same underlying file — e.g. an omnibus section header and its first
    // chapter both point at lesson_1.xhtml. Without this, the parent label
    // ("বিষকুম্ভ") would shadow the child ("০১. তাসের ঘর") and the
    // breadcrumb would lose the leaf.
    const match =
      matches.find(
        (entry) =>
          !Array.isArray(entry.subitems) || entry.subitems.length === 0,
      ) || matches[0];
    let label = "";
    if (match) {
      const ancestors = Array.isArray(match.ancestorLabels)
        ? match.ancestorLabels.filter((part) => part && part.trim())
        : [];
      const parts = [...ancestors, match.label || ""].filter(
        (part) => part && part.trim(),
      );
      label = parts.join(" › ");
    } else {
      label = this.lookupChapterLabel(target);
    }
    this.chapterLabelElement.textContent = label;
  },
  handleFullscreenStateChange() {
    if (this.getFullscreenElement() || !this.isImmersiveMode || !this.rendition)
      return;

    this.isImmersiveMode = false;
    removeClass(this.readerContainer, "immersive-reading");
    this.loadingIndicatorController.show();
    this.resetViewportScaleAfterFullscreenExit();
    this.stabilizeViewportResize([0, 140, 320, 620], 220, () => {
      this.loadingIndicatorController.hide();
    });
  },
  getFullscreenElement() {
    return (
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.webkitCurrentFullScreenElement ||
      null
    );
  },
  stabilizeViewportResize(delays = [0], resizeDelay = 0, onComplete) {
    this.clearFullscreenResizeTimers();

    if (!delays.length) {
      this.resizeReaderViewport(resizeDelay, onComplete);
      return;
    }

    delays.forEach((delay, index) => {
      const timerId = setTimeout(() => {
        this.resizeReaderViewport(
          resizeDelay,
          index === delays.length - 1 ? onComplete : undefined,
        );
      }, delay);

      this.fullscreenResizeTimers.push(timerId);
    });
  },
  resizeReaderViewport(delay = 0, onResized) {
    if (!this.rendition) {
      if (typeof onResized === "function") {
        onResized();
      }
      return;
    }

    const resizeRendition = () => {
      this.resizeReaderViewportRaf = requestAnimationFrame(() => {
        let width = this.readerWrapperContainer?.clientWidth || 0;
        let height = this.readerWrapperContainer?.clientHeight || 0;
        const viewerElement = query(SELECTORS.viewer);

        if ((!width || !height) && this.readerWrapperContainer) {
          const rect = this.readerWrapperContainer.getBoundingClientRect();
          width = rect.width;
          height = rect.height;
        }

        if ((!width || !height) && viewerElement) {
          width = viewerElement.clientWidth;
          height = viewerElement.clientHeight;
        }

        if (
          (!width || !height) &&
          window.visualViewport?.width &&
          window.visualViewport?.height
        ) {
          width = window.visualViewport.width;
          height = window.visualViewport.height;
        }

        width = Math.floor(width || 0);
        height = Math.floor(height || 0);

        if (
          width > 0 &&
          height > 0 &&
          typeof this.rendition?.resize === "function" &&
          this.rendition?.manager
        ) {
          this.rendition.resize(width, height);
          this.iframeBridgeController.waitForContentReady(() => {
            if (typeof onResized === "function") {
              onResized();
            }
          }, 5000);
          return;
        }

        if (typeof onResized === "function") {
          onResized();
        }
      });
    };

    this.clearViewportResizeWork();

    if (delay > 0) {
      this.resizeReaderViewportTimer = setTimeout(resizeRendition, delay);
      return;
    }

    resizeRendition();
  },
};
