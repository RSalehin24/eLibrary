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
  renderTocTree,
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

export const readerApplicationBookInitializationMethods = {
  initializeBook(source, options = {}) {
    const sessionId = this.beginReaderSession();
    this.teardownCurrentPublication({ clearViewer: true, clearToc: true });
    this.loadingIndicatorController.show();
    this.launchManifest = normalizeReaderManifestPayload(
      options.launchManifest || this.launchManifest,
      resolveAppUrl,
    );
    this.seedHighlightsFromManifest?.(this.launchManifest);
    const normalizedSource =
      typeof source === "string" ? resolveAppUrl(source) : source;

    let nextBook;
    try {
      nextBook = window.ePub(normalizedSource, {
        requestCredentials: true,
      });
    } catch (error) {
      try {
        nextBook = new window.ePub(normalizedSource, {
          requestCredentials: true,
        });
      } catch (fallbackError) {
        this.handleFatalBookError(
          "Failed to create EPUB instance.",
          fallbackError,
          sessionId,
        );
        return;
      }
    }

    this.book = nextBook;

    try {
      this.rendition = this.book.renderTo("viewer", {
        flow: "scrolled-doc",
        width: "100%",
        height: "100%",
      });
    } catch (error) {
      this.handleFatalBookError(
        "Failed to initialize EPUB rendition.",
        error,
        sessionId,
      );
      return;
    }

    this.attachRenditionEventHandlers(sessionId);

    const initialDisplayTarget = options.initialLocation || "";
    const displayPromise = initialDisplayTarget
      ? Promise.resolve(this.rendition.display(initialDisplayTarget)).catch(
          () => this.rendition.display(),
        )
      : Promise.resolve(this.rendition.display());

    displayPromise
      .then((location) => {
        if (!this.isSessionActive(sessionId)) return;

        const resolvedHref = this.normalizeHrefForComparison(
          location?.href || "",
        );
        if (resolvedHref) {
          this.currentHref = resolvedHref;
          this.syncSectionWithHref(resolvedHref);
        }

        this.readerThemeManager.attachThemesApi(this.rendition?.themes || null);
        this.readerThemeManager.registerThemes();
        this.readerThemeManager.setFontSize(
          `${this.readerThemeManager.getCurrentFontSize()}px`,
        );
        this.readerThemeManager.setTheme(
          this.readerThemeManager.getCurrentThemeIndex(),
          this.rendition,
        );
        this.syncReaderControlStates();
        this.setupSwipeGestures();

        return this.iframeBridgeController.waitForContentReady();
      })
      .then(() => {
        if (!this.isSessionActive(sessionId)) return;

        this.loadingIndicatorController.hide();
        if (this.currentHref) {
          syncSelectedTocItem(this.currentHref);
        }
        this.queueReadingStateSync(location);
        this.scheduleIframeInteractionSetup(
          IFRAME_INTERACTION_READY_DELAY_MS,
          sessionId,
        );
      })
      .catch((error) => {
        this.handleFatalBookError(
          "Failed to render selected EPUB.",
          error,
          sessionId,
        );
      });

    Promise.resolve(this.book.ready)
      .then(() => {
        if (!this.isSessionActive(sessionId)) return null;
        this.navigation = this.book.navigation;
        return this.book.locations?.generate?.() || null;
      })
      .then(() => {
        if (!this.isSessionActive(sessionId)) return;
        this.locations = this.book?.locations || null;
      })
      .catch((error) => {
        this.handleRecoverableBookError(
          "Failed to prepare book locations.",
          error,
          sessionId,
        );
      });

    Promise.resolve(this.book.loaded?.navigation)
      .then((navigation) => {
        if (!this.isSessionActive(sessionId) || !navigation) return;
        const flattenedToc = flattenToc(navigation.toc || []);
        this.flattenedToc = flattenedToc;
        renderTocTree(this.epubContents, navigation.toc || []);
        if (this.currentHref) {
          syncSelectedTocItem(this.currentHref);
          this.syncChapterLabel(this.currentHref);
        }
      })
      .catch((error) => {
        this.handleRecoverableBookError(
          "Failed to load table of contents.",
          error,
          sessionId,
        );
      });
  },
  attachRenditionEventHandlers(sessionId) {
    if (!this.rendition) return;

    this.rendition.on("rendered", () => {
      if (!this.isSessionActive(sessionId)) return;
      this.readerThemeManager.applyThemeToCurrentPage(
        this.readerThemeManager.getCurrentThemeIndex(),
        this.rendition,
      );
    });

    this.rendition.on("relocated", (location) => {
      if (!this.isSessionActive(sessionId)) return;

      const relocatedHref = this.normalizeHrefForComparison(
        location?.start?.href || location?.href || "",
      );
      if (relocatedHref) {
        this.currentHref = relocatedHref;
        this.syncSectionWithHref(relocatedHref);
        syncSelectedTocItem(relocatedHref);
      }

      this.queueReadingStateSync(location);
      this.scheduleIframeInteractionSetup(
        IFRAME_INTERACTION_RELOCATED_DELAY_MS,
        sessionId,
      );
    });

    this.attachHighlightEventHandlers?.(sessionId);
  },
  buildReadingStatePayload(location) {
    const normalizedHref = this.normalizeHrefForComparison(
      location?.start?.href || location?.href || this.currentHref || "",
    );
    const cfi =
      location?.start?.cfi ||
      this.book?.rendition?.currentLocation?.()?.start?.cfi ||
      "";
    let progressPercent = 0;

    if (this.book?.locations && cfi) {
      try {
        const percentage = this.book.locations.percentageFromCfi(cfi);
        if (Number.isFinite(percentage)) {
          progressPercent = Math.max(
            0,
            Math.min(100, Math.round(percentage * 1000) / 10),
          );
        }
      } catch {
        // Ignore percentage calculation errors for state sync.
      }
    }

    return {
      last_location: normalizedHref,
      progress_percent: progressPercent,
    };
  },
};
