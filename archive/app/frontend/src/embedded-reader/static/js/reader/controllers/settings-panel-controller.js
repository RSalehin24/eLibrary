import { addClass, hasClass, removeClass } from "../utils/dom-helpers.js";

export class SettingsPanelController {
  constructor({
    panelElement,
    triggerSelector = ".iconshezhi",
    iframeBridgeController
  } = {}) {
    this.panelElement = panelElement || null;
    this.triggerSelector = triggerSelector;
    this.iframeBridgeController = iframeBridgeController || null;

    this.documentClickHandler = null;
    this.windowBlurHandler = null;
    this.deferOpenTimer = null;
  }

  setPanelElement(panelElement) {
    this.panelElement = panelElement || null;
  }

  isOpen() {
    return hasClass(this.panelElement, "show");
  }

  syncTriggerAriaExpanded(isExpanded) {
    const trigger = document.querySelector(this.triggerSelector);
    if (!trigger) return;
    trigger.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  }

  toggle(event) {
    if (event?.stopPropagation) {
      event.stopPropagation();
    }

    if (this.isOpen()) {
      this.close();
      return;
    }

    this.open();
  }

  open() {
    if (!this.panelElement) return;

    addClass(this.panelElement, "show");
    this.panelElement.setAttribute("aria-hidden", "false");
    this.syncTriggerAriaExpanded(true);
    this.bindOutsideClickAndBlurHandlers();
  }

  close() {
    if (this.panelElement) {
      removeClass(this.panelElement, "show");
      this.panelElement.setAttribute("aria-hidden", "true");
    }

    this.syncTriggerAriaExpanded(false);
    this.unbindOutsideClickAndBlurHandlers();
  }

  bindOutsideClickAndBlurHandlers() {
    this.unbindOutsideClickAndBlurHandlers();

    this.deferOpenTimer = setTimeout(() => {
      this.documentClickHandler = (event) => {
        const target = event.target instanceof Element ? event.target : null;
        if (!target) return;

        if (
          !target.closest(".setting-wrapper") &&
          !target.closest(this.triggerSelector)
        ) {
          this.close();
        }
      };

      document.addEventListener("click", this.documentClickHandler);

      this.windowBlurHandler = () => {
        const iframeElement = this.iframeBridgeController?.getIframeElement?.();
        if (iframeElement && document.activeElement === iframeElement) {
          this.close();
        }
      };
      window.addEventListener("blur", this.windowBlurHandler);

      this.refreshIframeBinding();

      this.deferOpenTimer = null;
    }, 0);
  }

  unbindOutsideClickAndBlurHandlers() {
    if (this.deferOpenTimer) {
      clearTimeout(this.deferOpenTimer);
      this.deferOpenTimer = null;
    }

    if (this.documentClickHandler) {
      document.removeEventListener("click", this.documentClickHandler);
      this.documentClickHandler = null;
    }

    if (this.windowBlurHandler) {
      window.removeEventListener("blur", this.windowBlurHandler);
      this.windowBlurHandler = null;
    }

    this.iframeBridgeController?.detachDocumentListener("settingsPanelIframeClick");
  }

  refreshIframeBinding() {
    if (!this.isOpen()) return;

    this.iframeBridgeController?.attachDocumentListener({
      listenerKey: "settingsPanelIframeClick",
      eventName: "click",
      handler: () => {
        this.close();
      },
      shouldAttach: () => this.isOpen()
    });
  }

  destroy() {
    this.close();
  }
}
