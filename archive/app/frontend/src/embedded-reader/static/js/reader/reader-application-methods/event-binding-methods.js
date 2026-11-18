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

export const readerApplicationEventBindingMethods = {
  bindEvents() {
    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#open-new-book", (event) => {
        event.preventDefault();
        this.openNewBook();
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#open-shortcuts", (event) => {
        this.openShortcutsModal(event);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#close-shortcuts", (event) => {
        this.closeShortcutsModal(event);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#shortcut-modal", (event, target) => {
        this.closeShortcutsModal(event, target);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "change", "#open-epub", (event) => {
        this.handleBookFileSelection(event);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".prev-btn", () => {
        this.changePrev();
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".next-btn", () => {
        this.changeNext();
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".iconmulu", () => {
        this.toggleTocPanel();
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".toc-toggle", (event, target) => {
        event.stopPropagation();
        this.handleTocToggle(target);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", TOC_LABEL_SELECTOR, (event, target) => {
        this.handleTocSelection(event, target);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".iconshezhi", (event) => {
        this.toggleSettingsPanel(event);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".size-btn", (event, target) => {
        this.handleFontSizeControl(target);
      }),
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".bg-btn", (_, target) => {
        this.handleThemeControl(target);
      }),
    );
  },
  openNewBook() {
    if (!this.openEpubButton) return;
    this.openEpubButton.click();
  },
  openShortcutsModal(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    this.shortcutDialogController.open();
  },
  closeShortcutsModal(event, backdropElement) {
    if (backdropElement && event?.target !== backdropElement) {
      return;
    }

    this.shortcutDialogController.close();
  },
  handleBookFileSelection(event) {
    const file = event.target?.files?.[0];
    if (!file) return;

    this.closeSettings();
    this.closeShortcutsModal();
    showElementFlex(this.readerContainer);
    hideElement(this.openEbookPage);

    const reader = new FileReader();
    reader.onload = () => {
      const arrayBuffer = reader.result;
      this.initializeBook(arrayBuffer);
    };
    reader.onerror = () => {
      console.error("Failed to read selected EPUB file.");
      this.closeBook();
    };
    reader.onabort = () => {
      this.closeBook();
    };
    reader.readAsArrayBuffer(file);
  },
  handleTocToggle(toggleBtn) {
    const row = toggleBtn.closest(".slide-contents-item");
    if (!row) return;
    const node = row.parentElement;
    if (!node || !node.classList.contains("toc-node")) return;
    const children = node.querySelector(":scope > .toc-children");
    if (!children) return;
    const isOpen = !children.hidden;
    children.hidden = isOpen;
    toggleBtn.setAttribute("aria-expanded", String(!isOpen));
    toggleBtn.innerHTML = isOpen ? "&#9654;" : "&#9660;";
  },
  teardownCurrentPublication({ clearViewer = false, clearToc = false } = {}) {
    this.clearPendingIframeInteractionSetup();
    if (this.persistReadingStateTimer) {
      clearTimeout(this.persistReadingStateTimer);
      this.persistReadingStateTimer = null;
    }
    this.iframeBridgeController.reset();
    this.readerThemeManager.teardown();

    if (this.rendition) {
      try {
        this.rendition.destroy();
      } catch {
        // Ignore rendition teardown errors.
      }
      this.rendition = null;
    }

    if (this.book) {
      try {
        this.book.destroy();
      } catch {
        // Ignore book teardown errors.
      }
      this.book = null;
    }

    this.locations = null;
    this.navigation = null;
    this.currentHref = null;
    this.section = 0;
    this.flattenedToc = null;

    if (this.chapterLabelElement) {
      this.chapterLabelElement.textContent = "";
    }

    if (clearViewer && this.readerWrapperContainer) {
      removeClass(this.readerWrapperContainer, "stop");
      removeClass(this.readerWrapperContainer, "close");
      this.readerWrapperContainer.innerHTML = "";
    }

    if (clearToc && this.epubContents) {
      this.epubContents.innerHTML = "";
    }
  },
};
