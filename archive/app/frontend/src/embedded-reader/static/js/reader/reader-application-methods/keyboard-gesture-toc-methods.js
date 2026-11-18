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

export const readerApplicationKeyboardGestureTocMethods = {
  refresh(href) {
    const currentLocation = this.book?.rendition?.currentLocation?.();

    const cfi = currentLocation?.start?.cfi;
    if (this.book?.locations && cfi) {
      this.book.locations.percentageFromCfi(cfi);
    }

    const resolvedHref = this.normalizeHrefForComparison(
      currentLocation?.start?.href || currentLocation?.href || href || "",
    );
    if (!resolvedHref) return;

    this.currentHref = resolvedHref;
    this.syncSectionWithHref(resolvedHref);
    syncSelectedTocItem(resolvedHref);
    this.syncChapterLabel(resolvedHref);
  },
  setupKeyboardShortcuts() {
    this.keyboardHandler = (event) => {
      const keyEvent = event?.originalEvent || event;
      if (!keyEvent || keyEvent.defaultPrevented) return;

      const eventTarget =
        keyEvent.target instanceof Element ? keyEvent.target : null;
      const isEditableTarget =
        !!eventTarget &&
        (eventTarget.isContentEditable ||
          !!eventTarget.closest(
            "input, textarea, select, [contenteditable='true'], [contenteditable=''], [role='textbox']",
          ));

      if (isEditableTarget) return;

      const isShortcutModalOpen =
        !!this.shortcutDialogController?.modalElement?.classList?.contains(
          "is-open",
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
  },
  setupSwipeGestures() {
    if (this.readerWrapperContainer) {
      this.swipeBinder(this.readerWrapperContainer);
    }

    this.iframeBridgeController.attachSwipeGestures(this.swipeBinder);
  },
  setupReaderWrapperContainerModeToggle() {
    if (!this.readerWrapperContainer) return;

    bindDoubleTapToggle({
      element: this.readerWrapperContainer,
      onToggle: () => this.toggleImmersiveMode(),
      setLastGlobalTouchTime: (timestamp) => {
        this.lastIframeToggleTouch = timestamp;
      },
      getLastGlobalTouchTime: () => this.lastIframeToggleTouch,
    });
  },
  resolveInternalBookHref(href) {
    if (!href) return "";
    if (!href.startsWith("#")) return href;

    const baseHref =
      this.currentHref ||
      this.normalizeHrefForComparison(
        this.book?.rendition?.currentLocation?.()?.start?.href ||
          this.book?.rendition?.currentLocation?.()?.href ||
          "",
      );

    if (!baseHref) return href;
    return `${baseHref}${href}`;
  },
  handleInternalBookLinkNavigation(href) {
    const resolvedHref = this.resolveInternalBookHref(href);
    if (!resolvedHref) return;

    this.syncSectionWithHref(resolvedHref);
    this.display(resolvedHref, () => {
      this.refresh(resolvedHref);
    });
  },
  setupIframeInteractions(sessionId = this.readerSessionId) {
    if (!this.isSessionActive(sessionId) || !this.rendition) return;

    this.iframeBridgeController.attachInternalLinkInterceptor((href) => {
      if (!this.isSessionActive(sessionId)) return;
      this.handleInternalBookLinkNavigation(href);
    });

    this.iframeBridgeController.attachSwipeGestures(this.swipeBinder);
    this.iframeBridgeController.attachReaderModeToggle({
      onToggle: () => this.toggleImmersiveMode(),
      isInteractiveTarget: (target) =>
        !!target?.closest?.(TOC_TOGGLE_EXCLUDED_TARGETS),
      setLastGlobalTouchTime: (timestamp) => {
        this.lastIframeToggleTouch = timestamp;
      },
      getLastGlobalTouchTime: () => this.lastIframeToggleTouch,
    });
    this.iframeBridgeController.attachKeyboardShortcuts(this.keyboardHandler);
    this.settingsPanelController.refreshIframeBinding();
  },
  syncTocToggleAriaState() {
    const toggleButton = query(".iconmulu");
    if (!toggleButton || !this.epubContents) return;

    const isExpanded = !hasClass(this.epubContents, "close");
    toggleButton.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  },
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
  },
  toggleSettingsPanel(event) {
    this.syncReaderControlStates();
    this.settingsPanelController.toggle(event);
  },
  handleFontSizeControl(target) {
    const tag = target?.dataset?.tag;

    if (tag === "big") {
      this.changeFontSizeByStep(1);
    } else if (tag === "small") {
      this.changeFontSizeByStep(-1);
    }
  },
  handleThemeControl(target) {
    const nextTheme = Number.parseInt(target?.dataset?.type || "", 10);
    if (!Number.isInteger(nextTheme)) return;
    this.applyThemeByIndex(nextTheme);
  },
};
