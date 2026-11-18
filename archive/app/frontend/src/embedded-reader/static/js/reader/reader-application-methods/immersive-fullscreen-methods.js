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

export const readerApplicationImmersiveFullscreenMethods = {
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

    const readerWrapperElement =
      this.readerContainer.querySelector(".reader-wrapper");
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
,
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
          !/^user-scalable\s*=/.test(part),
      );

    if (
      !normalizedViewportParts.some((part) => /^viewport-fit\s*=/.test(part))
    ) {
      normalizedViewportParts.push("viewport-fit=cover");
    }

    normalizedViewportParts.push(
      "initial-scale=1",
      "minimum-scale=1",
      "maximum-scale=1",
      "user-scalable=no",
    );

    viewportMeta.setAttribute("content", normalizedViewportParts.join(", "));

    requestAnimationFrame(() => {
      window.scrollTo(0, 0);
    });

    this.clearViewportRestoreTimer(false);
    this.pendingViewportRestoreContent = originalViewportContent;

    this.viewportScaleResetTimer = setTimeout(() => {
      if (this.pendingViewportRestoreContent) {
        viewportMeta.setAttribute(
          "content",
          this.pendingViewportRestoreContent,
        );
      }

      this.pendingViewportRestoreContent = null;
      this.viewportScaleResetTimer = null;
    }, 420);
  }
,
  clearResizeTimers() {
    this.clearViewportResizeWork();
    this.clearFullscreenResizeTimers();
    this.clearPendingFullscreenEnter();
  }
,
};
