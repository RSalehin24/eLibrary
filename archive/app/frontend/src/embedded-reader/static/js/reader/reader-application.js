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
  toggleClass,
} from "./utils/dom-helpers.js";
import {
  flattenToc,
  getItemHref,
  renderToc,
  syncSelectedTocItem,
} from "./utils/toc-helpers.js";
import {
  bindDoubleTapToggle,
  createSwipeBinder,
} from "./utils/gesture-handlers.js";
import { resolveAppUrl } from "../../../../api/urls.js";
import { normalizeReaderManifestPayload } from "../../../../features/reader/manifest.js";
import { LoadingIndicatorController } from "./controllers/loading-indicator-controller.js";
import { ReaderThemeManager } from "./controllers/theme-manager.js";
import { ShortcutDialogController } from "./controllers/shortcut-dialog-controller.js";
import { IframeBridgeController } from "./controllers/iframe-bridge-controller.js";
import { SettingsPanelController } from "./controllers/settings-panel-controller.js";
import { readerApplicationStartupSessionMethods } from "./reader-application-methods/startup-session-methods.js";
import { readerApplicationEventBindingMethods } from "./reader-application-methods/event-binding-methods.js";
import { readerApplicationBookInitializationMethods } from "./reader-application-methods/book-initialization-methods.js";
import { readerApplicationReadingStateNavigationMethods } from "./reader-application-methods/reading-state-navigation-methods.js";
import { readerApplicationKeyboardGestureTocMethods } from "./reader-application-methods/keyboard-gesture-toc-methods.js";
import { readerApplicationThemeViewportMethods } from "./reader-application-methods/theme-viewport-methods.js";
import { readerApplicationImmersiveFullscreenMethods } from "./reader-application-methods/immersive-fullscreen-methods.js";
import { readerApplicationCleanupResizeMethods } from "./reader-application-methods/cleanup-resize-methods.js";
import { readerApplicationHighlightMethods } from "./reader-application-methods/highlight-methods.js";

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
      query("meta[name='viewport']")?.getAttribute("content") ||
      VIEWPORT_FALLBACK_CONTENT;

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
      minimumDuration: 180,
    });

    this.readerThemeManager = new ReaderThemeManager({
      containerElement: this.epubContainer,
      themeList: THEMES,
      defaultThemeIndex: initialThemeIndex,
      defaultFontSize: initialFontSize,
      fallbackThemeColor: APP_THEME_COLOR,
    });
    this.readerThemeManager.setInitialState({
      themeIndex: initialThemeIndex,
      fontSize: initialFontSize,
    });

    this.shortcutDialogController = new ShortcutDialogController({
      modalElement: query("#shortcut-modal"),
    });

    this.iframeBridgeController = new IframeBridgeController({
      iframeSelector: `${SELECTORS.viewer} iframe`,
    });

    this.settingsPanelController = new SettingsPanelController({
      panelElement: this.settingPanel,
      triggerSelector: ".iconshezhi",
      iframeBridgeController: this.iframeBridgeController,
    });

    this.swipeBinder = createSwipeBinder({
      onNext: () => this.changeNext(),
      onPrev: () => this.changePrev(),
      onChangeFontSize: (stepCount) => this.changeFontSizeByStep(stepCount),
      onCycleTheme: () => this.cycleTheme(),
    });
  }
}

Object.assign(
  ReaderApplication.prototype,
  readerApplicationStartupSessionMethods,
  readerApplicationEventBindingMethods,
  readerApplicationBookInitializationMethods,
  readerApplicationReadingStateNavigationMethods,
  readerApplicationKeyboardGestureTocMethods,
  readerApplicationThemeViewportMethods,
  readerApplicationImmersiveFullscreenMethods,
  readerApplicationCleanupResizeMethods,
  readerApplicationHighlightMethods,
);
