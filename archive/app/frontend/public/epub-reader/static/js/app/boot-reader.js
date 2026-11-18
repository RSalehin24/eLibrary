import { ensureEpubRuntime } from "../vendor/epub-runtime/runtime-entry.js";
import { ReaderApplication } from "../reader/reader-application.js";

let appInstance = null;
let bootPromise = null;

function bootReaderApplication() {
  if (appInstance) return;
  if (bootPromise) return;

  bootPromise = ensureEpubRuntime()
    .then(() => {
      if (appInstance) return;

      const nextInstance = new ReaderApplication();
      nextInstance.init();

      appInstance = nextInstance;
      window.__epubReaderApp = nextInstance;
    })
    .catch((error) => {
      console.error("Failed to initialize EPUB runtime:", error);
      appInstance = null;
      window.__epubReaderApp = null;
    })
    .finally(() => {
      if (!appInstance) {
        bootPromise = null;
      }
    });
}

if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", bootReaderApplication, { once: true });
} else {
  bootReaderApplication();
}

window.addEventListener(
  "beforeunload",
  () => {
    appInstance?.destroy?.();
    appInstance = null;
    bootPromise = null;
    window.__epubReaderApp = null;
  },
  { once: true }
);
