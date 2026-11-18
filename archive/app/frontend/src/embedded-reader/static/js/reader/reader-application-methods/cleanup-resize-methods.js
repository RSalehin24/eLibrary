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

export const readerApplicationCleanupResizeMethods = {
  clearPendingFullscreenEnter() {
    if (this.fullscreenEnterVerificationTimer) {
      clearTimeout(this.fullscreenEnterVerificationTimer);
      this.fullscreenEnterVerificationTimer = null;
    }
  }
,
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
,
  clearFullscreenResizeTimers() {
    this.fullscreenResizeTimers.forEach((timerId) => clearTimeout(timerId));
    this.fullscreenResizeTimers = [];
  }
,
  clearViewportRestoreTimer(restoreOriginalContent) {
    if (this.viewportScaleResetTimer) {
      clearTimeout(this.viewportScaleResetTimer);
      this.viewportScaleResetTimer = null;
    }

    if (restoreOriginalContent) {
      const restoreContent =
        this.pendingViewportRestoreContent || this.baseViewportContent;
      const viewportMeta = query("meta[name='viewport']");
      if (viewportMeta && restoreContent) {
        viewportMeta.setAttribute("content", restoreContent);
      }
    }

    this.pendingViewportRestoreContent = null;
  }
,
};
