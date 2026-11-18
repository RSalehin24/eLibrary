import { bindDoubleTapToggle } from "../utils/gesture-handlers.js";
import { query, queryAll } from "../utils/dom-helpers.js";
import {
  attachInternalLinkInterceptor as attachLinkInterceptor,
  detachInternalLinkInterceptor as detachLinkInterceptor,
  shouldIgnoreNavigableHref
} from "./iframe-link-interceptor.js";

const DEFAULT_IFRAME_SELECTOR = "#viewer iframe";
const DEFAULT_POLL_INTERVAL_MS = 100;
const DEFAULT_WAIT_TIMEOUT_MS = 5000;
const DEFAULT_CONTENT_READY_TIMEOUT_MS = 10000;

export class IframeBridgeController {
  constructor({
    iframeSelector = DEFAULT_IFRAME_SELECTOR,
    pollIntervalMs = DEFAULT_POLL_INTERVAL_MS
  } = {}) {
    this.iframeSelector = iframeSelector;
    this.pollIntervalMs = pollIntervalMs;
    this.pendingTimeouts = new Set();
    this.pendingAnimationFrames = new Set();
    this.documentListenerRegistry = new Map();
    this.internalLinkCleanupDocument = null;
  }

  getIframeElement() {
    return query(this.iframeSelector);
  }

  getDocument() {
    return this.getIframeElement()?.contentDocument || null;
  }

  scheduleTimeout(callback, delay) {
    const timerId = setTimeout(() => {
      this.pendingTimeouts.delete(timerId);
      callback();
    }, delay);

    this.pendingTimeouts.add(timerId);
    return timerId;
  }

  scheduleAnimationFrame(callback) {
    const rafId = requestAnimationFrame(() => {
      this.pendingAnimationFrames.delete(rafId);
      callback();
    });

    this.pendingAnimationFrames.add(rafId);
    return rafId;
  }

  clearScheduledWork() {
    this.pendingTimeouts.forEach((timerId) => clearTimeout(timerId));
    this.pendingTimeouts.clear();

    this.pendingAnimationFrames.forEach((rafId) => cancelAnimationFrame(rafId));
    this.pendingAnimationFrames.clear();
  }

  waitForDocument(maxWait = DEFAULT_WAIT_TIMEOUT_MS) {
    const startedAt = Date.now();

    return new Promise((resolve) => {
      const poll = () => {
        const doc = this.getDocument();
        if (doc) {
          resolve(doc);
          return;
        }

        if (Date.now() - startedAt >= maxWait) {
          resolve(null);
          return;
        }

        this.scheduleTimeout(poll, this.pollIntervalMs);
      };

      poll();
    });
  }

  waitForBody(maxWait = DEFAULT_WAIT_TIMEOUT_MS) {
    const startedAt = Date.now();

    return new Promise((resolve) => {
      const poll = () => {
        const doc = this.getDocument();
        if (doc?.body) {
          resolve(doc.body);
          return;
        }

        if (Date.now() - startedAt >= maxWait) {
          resolve(null);
          return;
        }

        this.scheduleTimeout(poll, this.pollIntervalMs);
      };

      poll();
    });
  }

  waitForContentReady(onDone, maxWait = DEFAULT_CONTENT_READY_TIMEOUT_MS) {
    const startedAt = Date.now();

    return new Promise((resolve) => {
      const finish = () => {
        const doc = this.getDocument();
        if (typeof onDone === "function") {
          onDone(doc || null);
        }
        resolve(doc || null);
      };

      const checkReady = () => {
        const doc = this.getDocument();
        const body = doc?.body;

        if (!body) {
          if (Date.now() - startedAt >= maxWait) {
            finish();
            return;
          }

          this.scheduleTimeout(checkReady, 60);
          return;
        }

        const readyStateDone = doc.readyState === "complete";
        const images = body.images ? Array.from(body.images) : queryAll("img", body);
        const imagesDone = images.every((img) => img.complete || img.naturalWidth > 0);

        if (readyStateDone && imagesDone) {
          finish();
          return;
        }

        if (Date.now() - startedAt >= maxWait) {
          finish();
          return;
        }

        this.scheduleTimeout(checkReady, 60);
      };

      checkReady();
    });
  }

  shouldIgnoreNavigableHref(href) {
    return shouldIgnoreNavigableHref(href);
  }

  attachDocumentListener({
    listenerKey,
    eventName,
    handler,
    options,
    shouldAttach,
    maxWait = DEFAULT_WAIT_TIMEOUT_MS
  }) {
    if (!listenerKey || !eventName || typeof handler !== "function") {
      return Promise.resolve(null);
    }

    return this.waitForDocument(maxWait).then((doc) => {
      if (!doc) return null;
      if (typeof shouldAttach === "function" && !shouldAttach()) return null;

      this.detachDocumentListener(listenerKey);

      try {
        doc.addEventListener(eventName, handler, options);
        this.documentListenerRegistry.set(listenerKey, {
          doc,
          eventName,
          handler,
          options
        });
      } catch {
        return null;
      }

      return doc;
    });
  }

  detachDocumentListener(listenerKey) {
    const record = this.documentListenerRegistry.get(listenerKey);
    if (!record) return;

    try {
      record.doc.removeEventListener(record.eventName, record.handler, record.options);
    } catch {
      // Ignore iframe listener teardown errors.
    }

    this.documentListenerRegistry.delete(listenerKey);
  }

  attachKeyboardShortcuts(handler, maxWait = DEFAULT_WAIT_TIMEOUT_MS) {
    return this.attachDocumentListener({
      listenerKey: "readerKeyboard",
      eventName: "keydown",
      handler,
      maxWait
    });
  }

  attachSwipeGestures(swipeBinder, maxWait = DEFAULT_WAIT_TIMEOUT_MS) {
    if (typeof swipeBinder !== "function") return Promise.resolve(null);

    return this.waitForBody(maxWait).then((body) => {
      if (!body) return null;

      try {
        swipeBinder(body);
      } catch {
        // Ignore iframe gesture attachment errors.
      }

      return body;
    });
  }

  attachReaderModeToggle(
    {
      onToggle,
      isInteractiveTarget,
      setLastGlobalTouchTime,
      getLastGlobalTouchTime
    },
    maxWait = DEFAULT_WAIT_TIMEOUT_MS
  ) {
    return this.waitForBody(maxWait).then((body) => {
      if (!body) return null;

      bindDoubleTapToggle({
        element: body,
        onToggle,
        isInteractiveTarget,
        setLastGlobalTouchTime,
        getLastGlobalTouchTime
      });

      return body;
    });
  }

  attachInternalLinkInterceptor(onNavigate, maxWait = DEFAULT_WAIT_TIMEOUT_MS) {
    return attachLinkInterceptor({
      controller: this,
      maxWait,
      onNavigate
    });
  }

  detachInternalLinkInterceptor() {
    detachLinkInterceptor({ controller: this });
  }

  reset() {
    this.clearScheduledWork();
    this.detachInternalLinkInterceptor();

    const listenerKeys = Array.from(this.documentListenerRegistry.keys());
    listenerKeys.forEach((listenerKey) => this.detachDocumentListener(listenerKey));
  }

  destroy() {
    this.reset();
  }
}
