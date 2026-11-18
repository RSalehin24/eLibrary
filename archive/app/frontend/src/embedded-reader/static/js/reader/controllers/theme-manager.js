import {
  APP_THEME_COLOR,
  DEFAULT_FONT_SIZE,
  DEFAULT_THEME_INDEX,
  FONT_SIZE_STEP,
  MAX_FONT_SIZE,
  MIN_FONT_SIZE,
  STORAGE_KEYS,
  THEMES,
} from "../reader-settings.js";
import { clamp } from "../utils/dom-helpers.js";
import {
  applyThemeContainerClass,
  applyThemeToCurrentPage,
  syncSystemThemeColor,
} from "./theme-page-application.js";

export class ReaderThemeManager {
  constructor({
    containerElement,
    defaultFontSize = DEFAULT_FONT_SIZE,
    defaultThemeIndex = DEFAULT_THEME_INDEX,
    fallbackThemeColor = APP_THEME_COLOR,
    fontStep = FONT_SIZE_STEP,
    maxFontSize = MAX_FONT_SIZE,
    minFontSize = MIN_FONT_SIZE,
    themeList = THEMES,
  } = {}) {
    this.containerElement = containerElement;
    this.themeList = themeList;
    this.currentThemeIndex = defaultThemeIndex;
    this.currentFontSize = defaultFontSize;
    this.minFontSize = minFontSize;
    this.maxFontSize = maxFontSize;
    this.fontStep = fontStep;
    this.fallbackThemeColor = fallbackThemeColor;
    this.themesApi = null;
    this.observedDocuments = new Set();
    this.pendingThemeApplyTimers = new Set();
  }

  attachThemesApi(themesApi) {
    this.themesApi = themesApi || null;
  }

  getTheme(index) {
    return this.themeList[index];
  }

  getCurrentThemeIndex() {
    return this.currentThemeIndex;
  }

  getCurrentFontSize() {
    return this.currentFontSize;
  }

  setInitialState({ themeIndex, fontSize }) {
    if (Number.isInteger(themeIndex) && this.themeList[themeIndex]) {
      this.currentThemeIndex = themeIndex;
    }

    if (Number.isFinite(fontSize)) {
      this.currentFontSize = clamp(
        fontSize,
        this.minFontSize,
        this.maxFontSize,
      );
    }

    // Apply the theme container class immediately so the correct background
    // is visible from the moment the reader initialises, without waiting
    // for the EPUB book to finish loading.
    applyThemeContainerClass(this.containerElement, this.currentThemeIndex);
  }

  registerThemes() {
    if (!this.themesApi) return;

    this.themeList.forEach((theme) => {
      this.themesApi.register(theme.name, theme.style);
    });
  }

  setFontSize(sizeValue) {
    if (!this.themesApi) return;

    this.themesApi.fontSize(sizeValue);
  }

  changeFontSizeByStep(stepCount) {
    if (!stepCount || !this.themesApi) return false;

    const nextSize = clamp(
      this.currentFontSize + this.fontStep * stepCount,
      this.minFontSize,
      this.maxFontSize,
    );

    if (nextSize === this.currentFontSize) return false;

    this.currentFontSize = nextSize;
    this.setFontSize(`${this.currentFontSize}px`);
    this.persistNumber(STORAGE_KEYS.fontSize, this.currentFontSize);
    return true;
  }

  applyThemeByIndex(themeIndex, rendition) {
    if (!this.themesApi || !this.getTheme(themeIndex)) return false;

    return this.setTheme(themeIndex, rendition);
  }

  cycleTheme(rendition) {
    if (!this.themesApi || !this.themeList.length) return false;

    const nextThemeIndex = (this.currentThemeIndex + 1) % this.themeList.length;
    return this.setTheme(nextThemeIndex, rendition);
  }

  setTheme(themeIndex, rendition) {
    const theme = this.getTheme(themeIndex);
    if (!theme || !this.themesApi) return false;

    this.themesApi.select(theme.name);
    this.currentThemeIndex = themeIndex;
    this.persistNumber(STORAGE_KEYS.themeIndex, themeIndex);

    this.applyThemeContainerClass(themeIndex);
    this.applyThemeToCurrentPage(themeIndex, rendition);
    this.syncSystemThemeColor(themeIndex);

    return true;
  }

  persistNumber(key, value) {
    try {
      window.localStorage.setItem(key, String(value));
    } catch {
      // Ignore storage errors and keep runtime behavior intact.
    }
  }

  clearPendingThemeApplyTimers() {
    this.pendingThemeApplyTimers.forEach((timerId) => clearTimeout(timerId));
    this.pendingThemeApplyTimers.clear();
  }

  scheduleThemeReapply(callback, delayMs) {
    const timerId = setTimeout(() => {
      this.pendingThemeApplyTimers.delete(timerId);
      callback();
    }, delayMs);

    this.pendingThemeApplyTimers.add(timerId);
  }

  disconnectThemeObserver(doc) {
    if (!doc) return;

    if (doc.__readerScrollContainer?.classList) {
      doc.__readerScrollContainer.classList.remove("reader-scroll-container");
    }
    doc.__readerScrollContainer = null;
    if (doc.body?.classList) {
      doc.body.classList.remove("reader-scroll-host");
    }

    if (doc.__readerThemeObserver) {
      doc.__readerThemeObserver.disconnect();
      doc.__readerThemeObserver = null;
    }

    if (doc.__readerThemeObserverRaf) {
      cancelAnimationFrame(doc.__readerThemeObserverRaf);
      doc.__readerThemeObserverRaf = null;
    }

    if (doc.__readerThemePendingNodes) {
      doc.__readerThemePendingNodes.clear();
      doc.__readerThemePendingNodes = null;
    }

    this.observedDocuments.delete(doc);
  }

  teardown() {
    this.clearPendingThemeApplyTimers();
    Array.from(this.observedDocuments).forEach((doc) =>
      this.disconnectThemeObserver(doc),
    );
  }

  applyThemeContainerClass(themeIndex) {
    applyThemeContainerClass(this.containerElement, themeIndex);
  }

  syncSystemThemeColor(themeIndex, fallbackColor = this.fallbackThemeColor) {
    syncSystemThemeColor({
      fallbackColor,
      fallbackThemeColor: this.fallbackThemeColor,
      selectedTheme: this.getTheme(themeIndex),
    });
  }

  applyThemeToCurrentPage(themeIndex, rendition) {
    applyThemeToCurrentPage({
      clearPendingThemeApplyTimers: () => this.clearPendingThemeApplyTimers(),
      disconnectThemeObserver: (doc) => this.disconnectThemeObserver(doc),
      observedDocuments: this.observedDocuments,
      rendition,
      scheduleThemeReapply: (callback, delayMs) =>
        this.scheduleThemeReapply(callback, delayMs),
      theme: this.getTheme(themeIndex),
      themeIndex,
    });
  }
}
