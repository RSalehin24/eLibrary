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

export const readerApplicationStartupSessionMethods = {
  initializeElements() {
    this.openEbookPage = query(SELECTORS.openEbookPage);
    this.epubContents = query(SELECTORS.epubContents);
    this.readerWrapper = query(SELECTORS.readerWrapper);
    this.openEpubButton = query(SELECTORS.openEpubButton);
    this.readerContainer = query(SELECTORS.readerContainer);
    this.readerWrapperContainer = query(SELECTORS.readerWrapperContainer);
    this.epubContainer = query(SELECTORS.epubContainer);
    this.settingPanel = query(SELECTORS.settingWrapper);
    this.chapterLabelElement = query(SELECTORS.chapterLabel);
    removeClass(this.readerWrapperContainer, "close");

    if (this.settingsPanelController) {
      this.settingsPanelController.setPanelElement(this.settingPanel);
    }
  },
  getStoredNumber(key) {
    try {
      const value = window.localStorage.getItem(key);
      if (value === null) return null;

      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    } catch {
      return null;
    }
  },
  beginReaderSession() {
    this.readerSessionId += 1;
    return this.readerSessionId;
  },
  isSessionActive(sessionId) {
    return sessionId === this.readerSessionId;
  },
  clearPendingIframeInteractionSetup() {
    if (!this.pendingIframeInteractionTimer) return;
    clearTimeout(this.pendingIframeInteractionTimer);
    this.pendingIframeInteractionTimer = null;
  },
  scheduleIframeInteractionSetup(
    delayMs = IFRAME_INTERACTION_READY_DELAY_MS,
    sessionId = this.readerSessionId,
  ) {
    this.clearPendingIframeInteractionSetup();

    this.pendingIframeInteractionTimer = setTimeout(() => {
      this.pendingIframeInteractionTimer = null;
      if (!this.isSessionActive(sessionId) || !this.rendition) return;
      this.setupIframeInteractions(sessionId);
    }, delayMs);
  },
  handleRecoverableBookError(contextMessage, error, sessionId) {
    if (!this.isSessionActive(sessionId)) return;
    console.error(contextMessage, error);
  },
  handleFatalBookError(contextMessage, error, sessionId) {
    if (!this.isSessionActive(sessionId)) return;
    console.error(contextMessage, error);
    this.loadingIndicatorController.hide();
    this.closeBook();
  },
  getLaunchManifestUrl() {
    try {
      const params = new URLSearchParams(window.location.search);
      return resolveAppUrl(params.get("manifest") || "");
    } catch {
      return "";
    }
  },
  loadManifestLaunchIfPresent() {
    const manifestUrl = this.getLaunchManifestUrl();
    if (!manifestUrl) return;

    this.loadingIndicatorController.show();
    fetch(manifestUrl, {
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `Manifest request failed with status ${response.status}`,
          );
        }
        return response.json();
      })
      .then((manifest) =>
        normalizeReaderManifestPayload(manifest, resolveAppUrl),
      )
      .then((manifest) => {
        if (!manifest?.epub_download_url) {
          throw new Error("Manifest did not provide an EPUB download URL.");
        }

        this.launchManifest = manifest;
        this.closeSettings();
        this.closeShortcutsModal();
        showElementFlex(this.readerContainer);
        hideElement(this.openEbookPage);
        this.initializeBook(manifest.epub_download_url, {
          initialLocation: manifest.reading_session?.last_location || "",
          launchManifest: manifest,
        });
      })
      .catch((error) => {
        console.error("Failed to load launch manifest.", error);
        this.loadingIndicatorController.hide();
      });
  },
  init() {
    if (this.hasInitialized) return;
    if (typeof window.ePub !== "function") {
      throw new Error(
        "EPUB runtime is not loaded. Expected window.ePub to be available.",
      );
    }

    this.hasInitialized = true;
    this.bindEvents();
    this.setupReaderWrapperContainerModeToggle();
    this.setupKeyboardShortcuts();
    this.syncTocToggleAriaState();
    this.syncReaderControlStates();

    this.readerThemeManager.syncSystemThemeColor(undefined, APP_THEME_COLOR);

    document.addEventListener("fullscreenchange", this.onFullscreenStateChange);
    document.addEventListener(
      "webkitfullscreenchange",
      this.onFullscreenStateChange,
    );
    this.loadManifestLaunchIfPresent();
  },
  destroy() {
    if (!this.hasInitialized) return;
    this.hasInitialized = false;

    this.cleanupHandlers.forEach((cleanup) => {
      try {
        cleanup();
      } catch {
        // Ignore delegated listener cleanup errors.
      }
    });
    this.cleanupHandlers = [];

    if (this.keyboardHandler) {
      document.removeEventListener("keydown", this.keyboardHandler);
      this.keyboardHandler = null;
    }

    document.removeEventListener(
      "fullscreenchange",
      this.onFullscreenStateChange,
    );
    document.removeEventListener(
      "webkitfullscreenchange",
      this.onFullscreenStateChange,
    );

    this.closeBook();
    this.settingsPanelController.destroy();
    this.shortcutDialogController.close();
    this.iframeBridgeController.destroy();
    this.readerThemeManager.teardown();
  },
};
