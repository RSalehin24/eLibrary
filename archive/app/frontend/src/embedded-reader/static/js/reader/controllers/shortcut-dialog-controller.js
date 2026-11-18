import { addClass, removeClass } from "../utils/dom-helpers.js";

const FOCUSABLE_SELECTOR =
  "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

export class ShortcutDialogController {
  constructor({ modalElement }) {
    this.modalElement = modalElement;
    this.lastFocusedElement = null;
    this.keydownHandler = (event) => this.handleKeydown(event);
  }

  isOpen() {
    return !!this.modalElement?.classList?.contains("is-open");
  }

  getFocusableElements() {
    if (!this.modalElement) return [];

    return Array.from(this.modalElement.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
      (element) => !element.hasAttribute("disabled")
    );
  }

  focusFirstElement() {
    const [firstFocusableElement] = this.getFocusableElements();
    if (!firstFocusableElement?.focus) return;

    const scheduleFocus =
      typeof requestAnimationFrame === "function"
        ? requestAnimationFrame
        : (callback) => setTimeout(callback, 0);

    scheduleFocus(() => {
      firstFocusableElement.focus();
    });
  }

  restoreFocus() {
    if (this.lastFocusedElement?.focus) {
      this.lastFocusedElement.focus();
    }

    this.lastFocusedElement = null;
  }

  handleKeydown(event) {
    if (!this.isOpen() || !event) return;

    if (event.key === "Escape") {
      event.preventDefault();
      this.close();
      return;
    }

    if (event.key !== "Tab") return;

    const focusableElements = this.getFocusableElements();
    if (!focusableElements.length) {
      event.preventDefault();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    const activeElement = document.activeElement;

    if (event.shiftKey && activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
      return;
    }

    if (!event.shiftKey && activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }

  open() {
    if (!this.modalElement) return;

    this.lastFocusedElement = document.activeElement || null;
    addClass(this.modalElement, "is-open");
    this.modalElement.setAttribute("aria-hidden", "false");
    addClass(document.body, "shortcut-modal-open");
    document.addEventListener("keydown", this.keydownHandler);
    this.focusFirstElement();
  }

  close() {
    if (!this.modalElement) return;

    removeClass(this.modalElement, "is-open");
    this.modalElement.setAttribute("aria-hidden", "true");
    removeClass(document.body, "shortcut-modal-open");
    document.removeEventListener("keydown", this.keydownHandler);
    this.restoreFocus();
  }
}
