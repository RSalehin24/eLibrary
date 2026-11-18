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

const BENGALI_DIGIT_MAP = "০১২৩৪৫৬৭৮৯";

function toLocalNumerals(str, lang) {
  if (!lang || !lang.toLowerCase().startsWith("bn")) return str;
  return String(str).replace(/[0-9]/g, (d) => BENGALI_DIGIT_MAP[d]);
}

function readCookie(name) {
  const pattern = new RegExp(`(?:^|; )${name}=([^;]*)`);
  const match = document.cookie.match(pattern);
  return match ? decodeURIComponent(match[1]) : "";
}

export const readerApplicationReadingStateNavigationMethods = {
  queueReadingStateSync(location) {
    const syncUrl = resolveAppUrl(this.launchManifest?.reading_session_url);
    if (!syncUrl) return;

    const payload = this.buildReadingStatePayload(location);
    if (!payload.last_location) return;

    if (this.persistReadingStateTimer) {
      clearTimeout(this.persistReadingStateTimer);
    }

    this.persistReadingStateTimer = setTimeout(() => {
      this.persistReadingStateTimer = null;
      const csrfToken = readCookie("csrftoken");
      fetch(syncUrl, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify(payload),
      }).catch((error) => {
        console.error("Failed to persist reading state.", error);
      });
    }, 350);
  },
  exitFullscreenIfActive() {
    if (!this.getFullscreenElement()) return;

    try {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {
          // Ignore fullscreen exit errors.
        });
        return;
      }

      if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
        return;
      }

      if (document.webkitCancelFullScreen) {
        document.webkitCancelFullScreen();
      }
    } catch {
      // Ignore fullscreen exit errors.
    }
  },
  closeBook() {
    this.beginReaderSession();
    this.clearPendingIframeInteractionSetup();

    this.isImmersiveMode = false;
    removeClass(this.readerContainer, "immersive-reading");
    this.exitFullscreenIfActive();

    this.clearResizeTimers();
    this.clearViewportRestoreTimer(true);

    this.closeSettings();
    this.closeShortcutsModal();

    this.teardownCurrentPublication({ clearViewer: true, clearToc: true });

    hideElement(this.readerContainer);
    if (this.openEpubButton) {
      this.openEpubButton.value = "";
    }

    this.loadingIndicatorController.reset();
    showElement(this.openEbookPage);
    this.syncTocToggleAriaState();
    this.syncReaderControlStates();
    this.readerThemeManager.syncSystemThemeColor(undefined, APP_THEME_COLOR);
  },
  getSectionCount() {
    if (Array.isArray(this.book?.spine?.spineItems)) {
      return this.book.spine.spineItems.length;
    }

    const numericLength = this.book?.spine?.length;
    return Number.isFinite(numericLength) ? numericLength : 0;
  },
  changePrev() {
    if (!this.rendition || this.section <= 0) return;

    this.section -= 1;
    this.displayCurrentSection();
  },
  changeNext() {
    const sectionCount = this.getSectionCount();
    if (
      !this.rendition ||
      sectionCount <= 0 ||
      this.section >= sectionCount - 1
    )
      return;

    this.section += 1;
    this.displayCurrentSection();
  },
  displayCurrentSection() {
    if (!this.book || typeof this.book.section !== "function") return;

    const nextSection = this.book.section(this.section);
    if (!nextSection?.href) return;

    this.display(nextSection.href, () => {
      this.refresh(nextSection.href);
    });
  },
  display(href, callback, sessionId = this.readerSessionId) {
    if (!this.isSessionActive(sessionId) || !this.book?.rendition) {
      return Promise.resolve(false);
    }

    this.loadingIndicatorController.show();

    const displayPromise = href
      ? this.book.rendition.display(href)
      : this.book.rendition.display();

    return Promise.resolve(displayPromise)
      .then((location) => {
        if (!this.isSessionActive(sessionId)) return false;

        const resolvedHref = this.normalizeHrefForComparison(
          location?.href || href || "",
        );
        if (resolvedHref) {
          this.currentHref = resolvedHref;
          this.syncSectionWithHref(resolvedHref);
        }

        this.readerThemeManager.applyThemeToCurrentPage(
          this.readerThemeManager.getCurrentThemeIndex(),
          this.rendition,
        );

        return this.iframeBridgeController.waitForContentReady();
      })
      .then(() => {
        if (!this.isSessionActive(sessionId)) return false;

        this.loadingIndicatorController.hide();
        this.scheduleIframeInteractionSetup(
          IFRAME_INTERACTION_READY_DELAY_MS,
          sessionId,
        );

        if (typeof callback === "function") {
          callback();
        }

        return true;
      })
      .catch((error) => {
        if (!this.isSessionActive(sessionId)) return false;
        console.error("Failed to display EPUB section.", error);
        this.loadingIndicatorController.hide();
        return false;
      });
  },
  normalizeHrefForComparison(href) {
    if (!href) return "";
    const hrefWithoutHash = String(href).split("#")[0];

    try {
      return decodeURIComponent(hrefWithoutHash);
    } catch {
      return hrefWithoutHash;
    }
  },
  syncSectionWithHref(href) {
    const normalizedHref = this.normalizeHrefForComparison(href);
    const spineItems = this.book?.spine?.spineItems;
    if (!normalizedHref || !Array.isArray(spineItems)) return;

    const sectionIndex = spineItems.findIndex((item) => {
      const itemHref = this.normalizeHrefForComparison(item?.href || "");
      if (!itemHref) return false;
      return (
        itemHref === normalizedHref ||
        itemHref.endsWith(`/${normalizedHref}`) ||
        normalizedHref.endsWith(itemHref)
      );
    });

    if (sectionIndex !== -1) {
      this.section = sectionIndex;
    }

    this.updateChapterBar(href);
  },
  updateChapterBar(href) {
    const nameEl = document.getElementById("reader-chapter-name");
    const locEl = document.getElementById("reader-location");
    if (!nameEl && !locEl) return;

    const toc = this.book?.navigation?.toc;
    const flat = toc ? flattenToc(toc) : [];
    const normalizedHref = this.normalizeHrefForComparison(href);

    // Collect ALL matching indexes (an omnibus section header and its first
    // chapter often share the same underlying file). Then prefer a leaf entry
    // (no subitems) so the breadcrumb shows e.g. "বিষকুম্ভ › ০১. তাসের ঘর"
    // instead of just the parent section "বিষকুম্ভ".
    const matchedIndexes = [];
    if (flat.length && normalizedHref) {
      for (let i = 0; i < flat.length; i++) {
        const itemHref = this.normalizeHrefForComparison(flat[i].href || "");
        if (
          itemHref &&
          (itemHref === normalizedHref ||
            normalizedHref.endsWith(`/${itemHref}`) ||
            itemHref.endsWith(`/${normalizedHref}`) ||
            normalizedHref.endsWith(itemHref))
        ) {
          matchedIndexes.push(i);
        }
      }
    }
    let matchIdx = -1;
    if (matchedIndexes.length) {
      const leafIdx = matchedIndexes.find((idx) => {
        const subs = flat[idx]?.subitems;
        return !Array.isArray(subs) || subs.length === 0;
      });
      matchIdx = leafIdx !== undefined ? leafIdx : matchedIndexes[0];
    }

    const lang = this.book?.packaging?.metadata?.language || "";

    if (nameEl) {
      if (matchIdx >= 0) {
        // Prefer the explicit ancestorLabels chain that flattenToc records
        // (more reliable than scanning earlier flat entries by level, which
        // breaks when sibling sub-trees are interleaved).
        const ancestors = Array.isArray(flat[matchIdx].ancestorLabels)
          ? flat[matchIdx].ancestorLabels.filter((p) => p && p.trim())
          : [];
        const crumb = [...ancestors, flat[matchIdx].label || ""].filter(
          (p) => p && p.trim(),
        );
        nameEl.textContent = crumb.join(" › ");
      } else {
        nameEl.textContent = "";
      }
    }
    if (locEl) {
      if (matchIdx >= 0 && flat.length > 0) {
        const raw = `${matchIdx + 1} / ${flat.length}`;
        locEl.textContent = toLocalNumerals(raw, lang);
      } else {
        locEl.textContent = "";
      }
    }
  },
};
