import {
  APP_THEME_COLOR,
  DEFAULT_THEME_INDEX,
  DEFAULT_FONT_SIZE,
  MIN_FONT_SIZE,
  MAX_FONT_SIZE,
  SELECTORS,
  STORAGE_KEYS,
  THEMES,
  VIEWPORT_FALLBACK_CONTENT
} from "./reader-settings.js";
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
  toggleClass
} from "./utils/dom-helpers.js";
import {
  flattenToc,
  getItemHref,
  renderToc,
  syncSelectedTocItem
} from "./utils/toc-helpers.js";
import { bindDoubleTapToggle, createSwipeBinder } from "./utils/gesture-handlers.js";
import { LoadingIndicatorController } from "./controllers/loading-indicator-controller.js";
import { ReaderThemeManager } from "./controllers/theme-manager.js";
import { ShortcutDialogController } from "./controllers/shortcut-dialog-controller.js";
import { IframeBridgeController } from "./controllers/iframe-bridge-controller.js";
import { SettingsPanelController } from "./controllers/settings-panel-controller.js";

const TOC_LABEL_SELECTOR = ".slide-contents-item-label";
const TOC_TOGGLE_EXCLUDED_TARGETS =
  "a, button, input, textarea, select, label, summary, [data-no-reader-toggle]";
const IFRAME_INTERACTION_READY_DELAY_MS = 200;
const IFRAME_INTERACTION_RELOCATED_DELAY_MS = 100;

export class ReaderApplication {
  constructor() {
    this.book = null;
    this.rendition = null;
    this.locations = null;
    this.navigation = null;
    this.currentHref = null;

    this.section = 0;
    this.isImmersiveMode = false;
    this.lastIframeToggleTouch = 0;

    this.resizeReaderViewportTimer = null;
    this.resizeReaderViewportRaf = null;
    this.fullscreenResizeTimers = [];
    this.viewportScaleResetTimer = null;
    this.pendingViewportRestoreContent = null;
    this.pendingIframeInteractionTimer = null;
    this.fullscreenEnterVerificationTimer = null;
    this.baseViewportContent =
      query("meta[name='viewport']")?.getAttribute("content") || VIEWPORT_FALLBACK_CONTENT;

    this.keyboardHandler = null;
    this.hasInitialized = false;
    this.readerSessionId = 0;
    this.launchManifest = null;
    this.persistReadingStateTimer = null;

    this.onFullscreenStateChange = this.handleFullscreenStateChange.bind(this);
    this.cleanupHandlers = [];

    this.initializeElements();
    const storedThemeIndex = this.getStoredNumber(STORAGE_KEYS.themeIndex);
    const storedFontSize = this.getStoredNumber(STORAGE_KEYS.fontSize);
    const initialThemeIndex =
      Number.isInteger(storedThemeIndex) && THEMES[storedThemeIndex]
        ? storedThemeIndex
        : DEFAULT_THEME_INDEX;
    const initialFontSize =
      Number.isFinite(storedFontSize) &&
      storedFontSize >= MIN_FONT_SIZE &&
      storedFontSize <= MAX_FONT_SIZE
        ? storedFontSize
        : DEFAULT_FONT_SIZE;

    this.loadingIndicatorController = new LoadingIndicatorController({
      container: this.readerWrapperContainer,
      minimumDuration: 180
    });

    this.readerThemeManager = new ReaderThemeManager({
      containerElement: this.epubContainer,
      themeList: THEMES,
      defaultThemeIndex: initialThemeIndex,
      defaultFontSize: initialFontSize,
      fallbackThemeColor: APP_THEME_COLOR
    });
    this.readerThemeManager.setInitialState({
      themeIndex: initialThemeIndex,
      fontSize: initialFontSize
    });

    this.shortcutDialogController = new ShortcutDialogController({
      modalElement: query("#shortcut-modal")
    });

    this.iframeBridgeController = new IframeBridgeController({
      iframeSelector: `${SELECTORS.viewer} iframe`
    });

    this.settingsPanelController = new SettingsPanelController({
      panelElement: this.settingPanel,
      triggerSelector: ".iconshezhi",
      iframeBridgeController: this.iframeBridgeController
    });

    this.swipeBinder = createSwipeBinder({
      onNext: () => this.changeNext(),
      onPrev: () => this.changePrev(),
      onChangeFontSize: (stepCount) => this.changeFontSizeByStep(stepCount),
      onCycleTheme: () => this.cycleTheme()
    });
  }

  initializeElements() {
    this.openEbookPage = query(SELECTORS.openEbookPage);
    this.epubContents = query(SELECTORS.epubContents);
    this.readerWrapper = query(SELECTORS.readerWrapper);
    this.openEpubButton = query(SELECTORS.openEpubButton);
    this.readerContainer = query(SELECTORS.readerContainer);
    this.readerWrapperContainer = query(SELECTORS.readerWrapperContainer);
    this.epubContainer = query(SELECTORS.epubContainer);
    this.settingPanel = query(SELECTORS.settingWrapper);
    removeClass(this.readerWrapperContainer, "close");

    if (this.settingsPanelController) {
      this.settingsPanelController.setPanelElement(this.settingPanel);
    }
  }

  getStoredNumber(key) {
    try {
      const value = window.localStorage.getItem(key);
      if (value === null) return null;

      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }

  beginReaderSession() {
    this.readerSessionId += 1;
    return this.readerSessionId;
  }

  isSessionActive(sessionId) {
    return sessionId === this.readerSessionId;
  }

  clearPendingIframeInteractionSetup() {
    if (!this.pendingIframeInteractionTimer) return;
    clearTimeout(this.pendingIframeInteractionTimer);
    this.pendingIframeInteractionTimer = null;
  }

  scheduleIframeInteractionSetup(
    delayMs = IFRAME_INTERACTION_READY_DELAY_MS,
    sessionId = this.readerSessionId
  ) {
    this.clearPendingIframeInteractionSetup();

    this.pendingIframeInteractionTimer = setTimeout(() => {
      this.pendingIframeInteractionTimer = null;
      if (!this.isSessionActive(sessionId) || !this.rendition) return;
      this.setupIframeInteractions(sessionId);
    }, delayMs);
  }

  handleRecoverableBookError(contextMessage, error, sessionId) {
    if (!this.isSessionActive(sessionId)) return;
    console.error(contextMessage, error);
  }

  handleFatalBookError(contextMessage, error, sessionId) {
    if (!this.isSessionActive(sessionId)) return;
    console.error(contextMessage, error);
    this.loadingIndicatorController.hide();
    this.closeBook();
  }

  getLaunchManifestUrl() {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("manifest") || "";
    } catch {
      return "";
    }
  }

  loadManifestLaunchIfPresent() {
    const manifestUrl = this.getLaunchManifestUrl();
    if (!manifestUrl) return;

    this.loadingIndicatorController.show();
    fetch(manifestUrl, {
      headers: {
        Accept: "application/json"
      }
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Manifest request failed with status ${response.status}`);
        }
        return response.json();
      })
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
          launchManifest: manifest
        });
      })
      .catch((error) => {
        console.error("Failed to load launch manifest.", error);
        this.loadingIndicatorController.hide();
      });
  }

  init() {
    if (this.hasInitialized) return;
    if (typeof window.ePub !== "function") {
      throw new Error("EPUB runtime is not loaded. Expected window.ePub to be available.");
    }

    this.hasInitialized = true;
    this.bindEvents();
    this.setupReaderWrapperContainerModeToggle();
    this.setupKeyboardShortcuts();
    this.syncTocToggleAriaState();
    this.syncReaderControlStates();

    this.readerThemeManager.syncSystemThemeColor(undefined, APP_THEME_COLOR);

    document.addEventListener("fullscreenchange", this.onFullscreenStateChange);
    document.addEventListener("webkitfullscreenchange", this.onFullscreenStateChange);
    this.loadManifestLaunchIfPresent();
  }

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

    document.removeEventListener("fullscreenchange", this.onFullscreenStateChange);
    document.removeEventListener("webkitfullscreenchange", this.onFullscreenStateChange);

    this.closeBook();
    this.settingsPanelController.destroy();
    this.shortcutDialogController.close();
    this.iframeBridgeController.destroy();
    this.readerThemeManager.teardown();
  }

  bindEvents() {
    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#open-new-book", (event) => {
        event.preventDefault();
        this.openNewBook();
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#open-shortcuts", (event) => {
        this.openShortcutsModal(event);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#close-shortcuts", (event) => {
        this.closeShortcutsModal(event);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", "#shortcut-modal", (event, target) => {
        this.closeShortcutsModal(event, target);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "change", "#open-epub", (event) => {
        this.handleBookFileSelection(event);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".prev-btn", () => {
        this.changePrev();
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".next-btn", () => {
        this.changeNext();
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".iconmulu", () => {
        this.toggleTocPanel();
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", TOC_LABEL_SELECTOR, (event, target) => {
        this.handleTocSelection(event, target);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".iconshezhi", (event) => {
        this.toggleSettingsPanel(event);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".size-btn", (event, target) => {
        this.handleFontSizeControl(target);
      })
    );

    this.cleanupHandlers.push(
      delegateEvent(document, "click", ".bg-btn", (_, target) => {
        this.handleThemeControl(target);
      })
    );
  }

  openNewBook() {
    if (!this.openEpubButton) return;
    this.openEpubButton.click();
  }

  openShortcutsModal(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    this.shortcutDialogController.open();
  }

  closeShortcutsModal(event, backdropElement) {
    if (backdropElement && event?.target !== backdropElement) {
      return;
    }

    this.shortcutDialogController.close();
  }

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
  }

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

    if (clearViewer && this.readerWrapperContainer) {
      removeClass(this.readerWrapperContainer, "stop");
      removeClass(this.readerWrapperContainer, "close");
      this.readerWrapperContainer.innerHTML = "";
    }

    if (clearToc && this.epubContents) {
      this.epubContents.innerHTML = "";
    }
  }

  initializeBook(source, options = {}) {
    const sessionId = this.beginReaderSession();
    this.teardownCurrentPublication({ clearViewer: true, clearToc: true });
    this.loadingIndicatorController.show();
    this.launchManifest = options.launchManifest || this.launchManifest;

    let nextBook;
    try {
      nextBook = window.ePub(source, {});
    } catch (error) {
      try {
        nextBook = new window.ePub(source, {});
      } catch (fallbackError) {
        this.handleFatalBookError("Failed to create EPUB instance.", fallbackError, sessionId);
        return;
      }
    }

    this.book = nextBook;

    try {
      this.rendition = this.book.renderTo("viewer", {
        flow: "scrolled-doc",
        width: "100%",
        height: "100%"
      });
    } catch (error) {
      this.handleFatalBookError("Failed to initialize EPUB rendition.", error, sessionId);
      return;
    }

    this.attachRenditionEventHandlers(sessionId);

    const initialDisplayTarget = options.initialLocation || "";
    const displayPromise = initialDisplayTarget
      ? Promise.resolve(this.rendition.display(initialDisplayTarget)).catch(() => this.rendition.display())
      : Promise.resolve(this.rendition.display());

    displayPromise
      .then((location) => {
        if (!this.isSessionActive(sessionId)) return;

        const resolvedHref = this.normalizeHrefForComparison(location?.href || "");
        if (resolvedHref) {
          this.currentHref = resolvedHref;
          this.syncSectionWithHref(resolvedHref);
        }

        this.readerThemeManager.attachThemesApi(this.rendition?.themes || null);
        this.readerThemeManager.registerThemes();
        this.readerThemeManager.setFontSize(`${this.readerThemeManager.getCurrentFontSize()}px`);
        this.readerThemeManager.setTheme(
          this.readerThemeManager.getCurrentThemeIndex(),
          this.rendition
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
        this.scheduleIframeInteractionSetup(IFRAME_INTERACTION_READY_DELAY_MS, sessionId);
      })
      .catch((error) => {
        this.handleFatalBookError("Failed to render selected EPUB.", error, sessionId);
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
        this.handleRecoverableBookError("Failed to prepare book locations.", error, sessionId);
      });

    Promise.resolve(this.book.loaded?.navigation)
      .then((navigation) => {
        if (!this.isSessionActive(sessionId) || !navigation) return;
        const flattenedToc = flattenToc(navigation.toc || []);
        renderToc(this.epubContents, flattenedToc);
        if (this.currentHref) {
          syncSelectedTocItem(this.currentHref);
        }
      })
      .catch((error) => {
        this.handleRecoverableBookError("Failed to load table of contents.", error, sessionId);
      });
  }

  attachRenditionEventHandlers(sessionId) {
    if (!this.rendition) return;

    this.rendition.on("rendered", () => {
      if (!this.isSessionActive(sessionId)) return;
      this.readerThemeManager.applyThemeToCurrentPage(
        this.readerThemeManager.getCurrentThemeIndex(),
        this.rendition
      );
    });

    this.rendition.on("relocated", (location) => {
      if (!this.isSessionActive(sessionId)) return;

      const relocatedHref = this.normalizeHrefForComparison(
        location?.start?.href || location?.href || ""
      );
      if (relocatedHref) {
        this.currentHref = relocatedHref;
        this.syncSectionWithHref(relocatedHref);
        syncSelectedTocItem(relocatedHref);
      }

      this.queueReadingStateSync(location);
      this.scheduleIframeInteractionSetup(IFRAME_INTERACTION_RELOCATED_DELAY_MS, sessionId);
    });
  }

  buildReadingStatePayload(location) {
    const normalizedHref = this.normalizeHrefForComparison(
      location?.start?.href || location?.href || this.currentHref || ""
    );
    const cfi = location?.start?.cfi || this.book?.rendition?.currentLocation?.()?.start?.cfi || "";
    let progressPercent = 0;

    if (this.book?.locations && cfi) {
      try {
        const percentage = this.book.locations.percentageFromCfi(cfi);
        if (Number.isFinite(percentage)) {
          progressPercent = Math.max(0, Math.min(100, Math.round(percentage * 1000) / 10));
        }
      } catch {
        // Ignore percentage calculation errors for state sync.
      }
    }

    return {
      last_location: normalizedHref,
      progress_percent: progressPercent
    };
  }

  queueReadingStateSync(location) {
    const syncUrl = this.launchManifest?.reading_session_url;
    if (!syncUrl) return;

    const payload = this.buildReadingStatePayload(location);
    if (!payload.last_location) return;

    if (this.persistReadingStateTimer) {
      clearTimeout(this.persistReadingStateTimer);
    }

    this.persistReadingStateTimer = setTimeout(() => {
      this.persistReadingStateTimer = null;
      fetch(syncUrl, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      }).catch((error) => {
        console.error("Failed to persist reading state.", error);
      });
    }, 350);
  }

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
  }

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
  }

  getSectionCount() {
    if (Array.isArray(this.book?.spine?.spineItems)) {
      return this.book.spine.spineItems.length;
    }

    const numericLength = this.book?.spine?.length;
    return Number.isFinite(numericLength) ? numericLength : 0;
  }

  changePrev() {
    if (!this.rendition || this.section <= 0) return;

    this.section -= 1;
    this.displayCurrentSection();
  }

  changeNext() {
    const sectionCount = this.getSectionCount();
    if (!this.rendition || sectionCount <= 0 || this.section >= sectionCount - 1) return;

    this.section += 1;
    this.displayCurrentSection();
  }

  displayCurrentSection() {
    if (!this.book || typeof this.book.section !== "function") return;

    const nextSection = this.book.section(this.section);
    if (!nextSection?.href) return;

    this.display(nextSection.href, () => {
      this.refresh(nextSection.href);
    });
  }

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

        const resolvedHref = this.normalizeHrefForComparison(location?.href || href || "");
        if (resolvedHref) {
          this.currentHref = resolvedHref;
          this.syncSectionWithHref(resolvedHref);
        }

        this.readerThemeManager.applyThemeToCurrentPage(
          this.readerThemeManager.getCurrentThemeIndex(),
          this.rendition
        );

        return this.iframeBridgeController.waitForContentReady();
      })
      .then(() => {
        if (!this.isSessionActive(sessionId)) return false;

        this.loadingIndicatorController.hide();
        this.scheduleIframeInteractionSetup(IFRAME_INTERACTION_READY_DELAY_MS, sessionId);

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
  }

  normalizeHrefForComparison(href) {
    if (!href) return "";
    const hrefWithoutHash = String(href).split("#")[0];

    try {
      return decodeURIComponent(hrefWithoutHash);
    } catch {
      return hrefWithoutHash;
    }
  }

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
  }

  refresh(href) {
    const currentLocation = this.book?.rendition?.currentLocation?.();

    const cfi = currentLocation?.start?.cfi;
    if (this.book?.locations && cfi) {
      this.book.locations.percentageFromCfi(cfi);
    }

    const resolvedHref = this.normalizeHrefForComparison(
      currentLocation?.start?.href || currentLocation?.href || href || ""
    );
    if (!resolvedHref) return;

    this.currentHref = resolvedHref;
    this.syncSectionWithHref(resolvedHref);
    syncSelectedTocItem(resolvedHref);
  }

  setupKeyboardShortcuts() {
    this.keyboardHandler = (event) => {
      const keyEvent = event?.originalEvent || event;
      if (!keyEvent || keyEvent.defaultPrevented) return;

      const eventTarget = keyEvent.target instanceof Element ? keyEvent.target : null;
      const isEditableTarget =
        !!eventTarget &&
        (eventTarget.isContentEditable ||
          !!eventTarget.closest(
            "input, textarea, select, [contenteditable='true'], [contenteditable=''], [role='textbox']"
          ));

      if (isEditableTarget) return;

      const isShortcutModalOpen = !!this.shortcutDialogController?.modalElement?.classList?.contains(
        "is-open"
      );

      if (isShortcutModalOpen && keyEvent.key !== "Escape") {
        return;
      }

      const isModifierPressed = keyEvent.metaKey || keyEvent.ctrlKey;
      const key = (keyEvent.key || "").toLowerCase();
      const isToggleFullscreenKey =
        key === "f" || keyEvent.code === "KeyF" || keyEvent.keyCode === 70;

      if (!isModifierPressed) {
        if (keyEvent.key === "ArrowLeft" || keyEvent.keyCode === 37) {
          this.changePrev();
        } else if (keyEvent.key === "ArrowRight" || keyEvent.keyCode === 39) {
          this.changeNext();
        } else if (keyEvent.key === "Escape") {
          this.closeShortcutsModal();
          this.closeSettings();
        } else if (isToggleFullscreenKey && this.rendition) {
          keyEvent.preventDefault();
          this.toggleImmersiveMode();
        }
        return;
      }

      if (keyEvent.key === "1") {
        keyEvent.preventDefault();
        this.applyThemeByIndex(0);
      } else if (keyEvent.key === "2") {
        keyEvent.preventDefault();
        this.applyThemeByIndex(1);
      } else if (keyEvent.key === "3") {
        keyEvent.preventDefault();
        this.applyThemeByIndex(2);
      } else if (keyEvent.key === "+" || keyEvent.key === "=") {
        keyEvent.preventDefault();
        this.changeFontSizeByStep(1);
      } else if (keyEvent.key === "-") {
        keyEvent.preventDefault();
        this.changeFontSizeByStep(-1);
      }
    };

    document.addEventListener("keydown", this.keyboardHandler);
  }

  setupSwipeGestures() {
    if (this.readerWrapperContainer) {
      this.swipeBinder(this.readerWrapperContainer);
    }

    this.iframeBridgeController.attachSwipeGestures(this.swipeBinder);
  }

  setupReaderWrapperContainerModeToggle() {
    if (!this.readerWrapperContainer) return;

    bindDoubleTapToggle({
      element: this.readerWrapperContainer,
      onToggle: () => this.toggleImmersiveMode(),
      setLastGlobalTouchTime: (timestamp) => {
        this.lastIframeToggleTouch = timestamp;
      },
      getLastGlobalTouchTime: () => this.lastIframeToggleTouch
    });
  }

  resolveInternalBookHref(href) {
    if (!href) return "";
    if (!href.startsWith("#")) return href;

    const baseHref =
      this.currentHref ||
      this.normalizeHrefForComparison(
        this.book?.rendition?.currentLocation?.()?.start?.href ||
          this.book?.rendition?.currentLocation?.()?.href ||
          ""
      );

    if (!baseHref) return href;
    return `${baseHref}${href}`;
  }

  handleInternalBookLinkNavigation(href) {
    const resolvedHref = this.resolveInternalBookHref(href);
    if (!resolvedHref) return;

    this.syncSectionWithHref(resolvedHref);
    this.display(resolvedHref, () => {
      this.refresh(resolvedHref);
    });
  }

  setupIframeInteractions(sessionId = this.readerSessionId) {
    if (!this.isSessionActive(sessionId) || !this.rendition) return;

    this.iframeBridgeController.attachInternalLinkInterceptor((href) => {
      if (!this.isSessionActive(sessionId)) return;
      this.handleInternalBookLinkNavigation(href);
    });

    this.iframeBridgeController.attachSwipeGestures(this.swipeBinder);
    this.iframeBridgeController.attachReaderModeToggle({
      onToggle: () => this.toggleImmersiveMode(),
      isInteractiveTarget: (target) => !!target?.closest?.(TOC_TOGGLE_EXCLUDED_TARGETS),
      setLastGlobalTouchTime: (timestamp) => {
        this.lastIframeToggleTouch = timestamp;
      },
      getLastGlobalTouchTime: () => this.lastIframeToggleTouch
    });
    this.iframeBridgeController.attachKeyboardShortcuts(this.keyboardHandler);
    this.settingsPanelController.refreshIframeBinding();
  }

  syncTocToggleAriaState() {
    const toggleButton = query(".iconmulu");
    if (!toggleButton || !this.epubContents) return;

    const isExpanded = !hasClass(this.epubContents, "close");
    toggleButton.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  }

  toggleTocPanel() {
    const isClosed = hasClass(this.epubContents, "close");

    if (isClosed) {
      removeClass(this.epubContents, "close");
      removeClass(this.readerWrapper, "close");
      removeClass(this.readerWrapperContainer, "close");
    } else {
      addClass(this.epubContents, "close");
      addClass(this.readerWrapper, "close");
      removeClass(this.readerWrapperContainer, "close");
    }

    this.syncTocToggleAriaState();

    this.loadingIndicatorController.show();
    this.resizeReaderViewport(320, () => {
      this.loadingIndicatorController.hide();
    });
  }

  toggleSettingsPanel(event) {
    this.syncReaderControlStates();
    this.settingsPanelController.toggle(event);
  }

  handleFontSizeControl(target) {
    const tag = target?.dataset?.tag;

    if (tag === "big") {
      this.changeFontSizeByStep(1);
    } else if (tag === "small") {
      this.changeFontSizeByStep(-1);
    }
  }

  handleThemeControl(target) {
    const nextTheme = Number.parseInt(target?.dataset?.type || "", 10);
    if (!Number.isInteger(nextTheme)) return;
    this.applyThemeByIndex(nextTheme);
  }

  handleTocSelection(event, target) {
    event.preventDefault();

    const rawHref = getItemHref(target);
    const normalizedHref = this.normalizeHrefForComparison(rawHref);
    if (!normalizedHref) return;

    this.syncSectionWithHref(normalizedHref);
    this.display(rawHref, () => {
      this.refresh(rawHref);
    });
  }

  applyThemeByIndex(themeIndex) {
    const isApplied = this.readerThemeManager.applyThemeByIndex(themeIndex, this.rendition);
    if (isApplied) {
      this.syncThemeControlState();
    }
    return isApplied;
  }

  cycleTheme() {
    const isApplied = this.readerThemeManager.cycleTheme(this.rendition);
    if (isApplied) {
      this.syncThemeControlState();
    }
    return isApplied;
  }

  changeFontSizeByStep(stepCount) {
    const hasChanged = this.readerThemeManager.changeFontSizeByStep(stepCount);
    this.syncFontControlState();
    return hasChanged;
  }

  closeSettings() {
    this.settingsPanelController.close();
  }

  syncThemeControlState() {
    const currentThemeIndex = this.readerThemeManager.getCurrentThemeIndex();

    queryAll(".bg-btn").forEach((button) => {
      const buttonThemeIndex = Number.parseInt(button?.dataset?.type || "", 10);
      const isActive = Number.isInteger(buttonThemeIndex) && buttonThemeIndex === currentThemeIndex;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  syncFontControlState() {
    const currentFontSize = this.readerThemeManager.getCurrentFontSize();
    const isAtMinimum = currentFontSize <= MIN_FONT_SIZE;
    const isAtMaximum = currentFontSize >= MAX_FONT_SIZE;

    queryAll(".size-btn").forEach((button) => {
      const tag = button?.dataset?.tag;
      const isDisabled = (tag === "small" && isAtMinimum) || (tag === "big" && isAtMaximum);
      button.disabled = isDisabled;
      button.setAttribute("aria-disabled", isDisabled ? "true" : "false");
    });
  }

  syncReaderControlStates() {
    this.syncThemeControlState();
    this.syncFontControlState();
  }

  handleFullscreenStateChange() {
    if (this.getFullscreenElement() || !this.isImmersiveMode || !this.rendition) return;

    this.isImmersiveMode = false;
    removeClass(this.readerContainer, "immersive-reading");
    this.loadingIndicatorController.show();
    this.resetViewportScaleAfterFullscreenExit();
    this.stabilizeViewportResize([0, 140, 320, 620], 220, () => {
      this.loadingIndicatorController.hide();
    });
  }

  getFullscreenElement() {
    return (
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.webkitCurrentFullScreenElement ||
      null
    );
  }

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
          index === delays.length - 1 ? onComplete : undefined
        );
      }, delay);

      this.fullscreenResizeTimers.push(timerId);
    });
  }

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

        if (width > 0 && height > 0) {
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
  }

  toggleImmersiveMode(forceState) {
    if (!this.readerContainer) return;
    if (!this.rendition && typeof forceState !== "boolean") return;

    const nextState =
      typeof forceState === "boolean" ? forceState : !this.isImmersiveMode;

    const requestFullscreen = (target) => {
      if (!target) return null;
      if (target.requestFullscreen) {
        return target.requestFullscreen.call(target);
      }
      if (target.webkitRequestFullscreen) {
        return target.webkitRequestFullscreen.call(target);
      }
      if (target.webkitRequestFullScreen) {
        return target.webkitRequestFullScreen.call(target);
      }
      return null;
    };

    const exitFullscreen = () => {
      if (document.exitFullscreen) {
        return document.exitFullscreen.call(document);
      }
      if (document.webkitExitFullscreen) {
        return document.webkitExitFullscreen.call(document);
      }
      if (document.webkitCancelFullScreen) {
        return document.webkitCancelFullScreen.call(document);
      }
      return null;
    };

    const finalizeEnter = () => {
      if (!this.rendition) return;
      this.loadingIndicatorController.show();
      this.stabilizeViewportResize([0, 120, 280, 520], 0, () => {
        this.loadingIndicatorController.hide();
      });
    };

    const finalizeExit = () => {
      if (!this.rendition) return;
      this.loadingIndicatorController.show();
      this.resetViewportScaleAfterFullscreenExit();
      this.stabilizeViewportResize([0, 140, 320, 620], 220, () => {
        this.loadingIndicatorController.hide();
      });
    };

    this.isImmersiveMode = nextState;
    toggleClass(this.readerContainer, "immersive-reading", nextState);

    if (!nextState) {
      this.clearPendingFullscreenEnter();
      const completeExit = () => {
        removeClass(this.readerContainer, "immersive-reading");
        finalizeExit();
      };

      if (this.getFullscreenElement()) {
        try {
          const exitResult = exitFullscreen();
          if (exitResult?.then) {
            exitResult.then(completeExit).catch(() => {
              completeExit();
            });
          } else {
            completeExit();
          }
        } catch {
          completeExit();
        }
      } else {
        completeExit();
      }

      return;
    }

    const readerWrapperElement = this.readerContainer.querySelector(".reader-wrapper");
    if (!readerWrapperElement) {
      finalizeEnter();
      return;
    }

    const supportsElementFullscreen = !!(
      readerWrapperElement.requestFullscreen ||
      readerWrapperElement.webkitRequestFullscreen ||
      readerWrapperElement.webkitRequestFullScreen
    );

    const rollbackEnterWithoutFullscreen = () => {
      if (this.getFullscreenElement()) {
        finalizeEnter();
        return;
      }

      this.isImmersiveMode = false;
      removeClass(this.readerContainer, "immersive-reading");
      this.loadingIndicatorController.hide();
    };

    this.clearPendingFullscreenEnter();

    // Force layout commit in the same event task before requesting fullscreen.
    readerWrapperElement.getBoundingClientRect();
    this.readerContainer.getBoundingClientRect();

    try {
      const requestResult = requestFullscreen(readerWrapperElement);

      if (requestResult?.then) {
        requestResult
          .then(() => {
            if (this.getFullscreenElement() || !supportsElementFullscreen) {
              finalizeEnter();
              return;
            }
            rollbackEnterWithoutFullscreen();
          })
          .catch(() => {
            rollbackEnterWithoutFullscreen();
          });
        return;
      }

      if (!supportsElementFullscreen) {
        finalizeEnter();
        return;
      }

      this.fullscreenEnterVerificationTimer = setTimeout(() => {
        this.fullscreenEnterVerificationTimer = null;
        if (this.getFullscreenElement()) {
          finalizeEnter();
          return;
        }
        rollbackEnterWithoutFullscreen();
      }, 140);
    } catch {
      rollbackEnterWithoutFullscreen();
    }
  }

  resetViewportScaleAfterFullscreenExit() {
    const viewportMeta = query("meta[name='viewport']");
    if (!viewportMeta) return;

    const preservedViewportContent =
      this.pendingViewportRestoreContent || this.baseViewportContent;
    const originalViewportContent =
      preservedViewportContent ||
      viewportMeta.getAttribute("content") ||
      VIEWPORT_FALLBACK_CONTENT;

    const normalizedViewportParts = originalViewportContent
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .filter(
        (part) =>
          !/^initial-scale\s*=/.test(part) &&
          !/^minimum-scale\s*=/.test(part) &&
          !/^maximum-scale\s*=/.test(part) &&
          !/^user-scalable\s*=/.test(part)
      );

    if (!normalizedViewportParts.some((part) => /^viewport-fit\s*=/.test(part))) {
      normalizedViewportParts.push("viewport-fit=cover");
    }

    normalizedViewportParts.push(
      "initial-scale=1",
      "minimum-scale=1",
      "maximum-scale=1",
      "user-scalable=no"
    );

    viewportMeta.setAttribute("content", normalizedViewportParts.join(", "));

    requestAnimationFrame(() => {
      window.scrollTo(0, 0);
    });

    this.clearViewportRestoreTimer(false);
    this.pendingViewportRestoreContent = originalViewportContent;

    this.viewportScaleResetTimer = setTimeout(() => {
      if (this.pendingViewportRestoreContent) {
        viewportMeta.setAttribute("content", this.pendingViewportRestoreContent);
      }

      this.pendingViewportRestoreContent = null;
      this.viewportScaleResetTimer = null;
    }, 420);
  }

  clearResizeTimers() {
    this.clearViewportResizeWork();
    this.clearFullscreenResizeTimers();
    this.clearPendingFullscreenEnter();
  }

  clearPendingFullscreenEnter() {
    if (this.fullscreenEnterVerificationTimer) {
      clearTimeout(this.fullscreenEnterVerificationTimer);
      this.fullscreenEnterVerificationTimer = null;
    }
  }

  clearViewportResizeWork() {
    if (this.resizeReaderViewportTimer) {
      clearTimeout(this.resizeReaderViewportTimer);
      this.resizeReaderViewportTimer = null;
    }

    if (this.resizeReaderViewportRaf) {
      cancelAnimationFrame(this.resizeReaderViewportRaf);
      this.resizeReaderViewportRaf = null;
    }
  }

  clearFullscreenResizeTimers() {
    this.fullscreenResizeTimers.forEach((timerId) => clearTimeout(timerId));
    this.fullscreenResizeTimers = [];
  }

  clearViewportRestoreTimer(restoreOriginalContent) {
    if (this.viewportScaleResetTimer) {
      clearTimeout(this.viewportScaleResetTimer);
      this.viewportScaleResetTimer = null;
    }

    if (restoreOriginalContent) {
      const restoreContent = this.pendingViewportRestoreContent || this.baseViewportContent;
      const viewportMeta = query("meta[name='viewport']");
      if (viewportMeta && restoreContent) {
        viewportMeta.setAttribute("content", restoreContent);
      }
    }

    this.pendingViewportRestoreContent = null;
  }
}
