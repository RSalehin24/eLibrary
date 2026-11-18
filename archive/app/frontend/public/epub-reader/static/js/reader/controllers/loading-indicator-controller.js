import { addClass, removeClass } from "../utils/dom-helpers.js";

export class LoadingIndicatorController {
  constructor({ container, minimumDuration = 180 }) {
    this.container = container;
    this.minimumDuration = minimumDuration;
    this.loaderShownAt = 0;
    this.hideTimer = null;
  }

  show() {
    if (!this.container) return;

    if (this.hideTimer) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }

    this.loaderShownAt = Date.now();
    removeClass(this.container, "stop");
    addClass(this.container, "loading");
  }

  hide() {
    if (!this.container) return;

    const elapsed = Date.now() - this.loaderShownAt;
    const waitTime = Math.max(0, this.minimumDuration - elapsed);

    if (this.hideTimer) {
      clearTimeout(this.hideTimer);
    }

    this.hideTimer = setTimeout(() => {
      addClass(this.container, "stop");
      removeClass(this.container, "loading");
      this.hideTimer = null;
    }, waitTime);
  }

  reset() {
    if (this.hideTimer) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }

    if (!this.container) return;

    removeClass(this.container, "loading");
    removeClass(this.container, "stop");
  }
}
