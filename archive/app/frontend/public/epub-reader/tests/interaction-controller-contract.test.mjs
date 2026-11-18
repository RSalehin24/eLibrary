import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function readProjectFile(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), "utf8");
}

test("shortcut modal controller includes focus trap and focus restore behavior", () => {
  const controller = readProjectFile(
    "static/js/reader/controllers/shortcut-dialog-controller.js"
  );
  assert.match(controller, /FOCUSABLE_SELECTOR/);
  assert.match(controller, /document\.addEventListener\("keydown", this\.keydownHandler\)/);
  assert.match(controller, /document\.removeEventListener\("keydown", this\.keydownHandler\)/);
  assert.match(controller, /event\.key !== "Tab"/);
  assert.match(controller, /restoreFocus\(\)/);
});

test("reader settings controls include active and disabled visual states", () => {
  const readerCss = readProjectFile("static/css/components/reader-layout.css");
  assert.match(readerCss, /\.bg-btn\.is-active/);
  assert.match(readerCss, /\.bg-btn\[aria-pressed="true"\]/);
  assert.match(readerCss, /\.size-btn:disabled/);
});

test("toc toggle does not rely on viewer legacy close class", () => {
  const readerApp = readProjectFile("static/js/reader/reader-application.js");
  assert.doesNotMatch(
    readerApp,
    /addClass\(this\.readerWrapperContainer,\s*"close"\)/
  );
});

test("theme manager keeps scrolling resilient with inner-container fallback", () => {
  const themeManager = readProjectFile("static/js/reader/controllers/theme-manager.js");
  assert.match(themeManager, /validateScrollContainer/);
  assert.match(themeManager, /currentContainer\.scrollHeight > currentContainer\.clientHeight \+ 1/);
  assert.match(themeManager, /const bodyCanScroll = body\.scrollHeight > body\.clientHeight \+ 1;/);
  assert.match(themeManager, /!bodyCanScroll &&/);
  assert.match(themeManager, /body\.classList\.remove\("reader-scroll-host"\)/);
  assert.match(themeManager, /body\.reader-scroll-host[\s\S]*overflow-y:\s*auto\s*!important;/);
  assert.match(themeManager, /const isDocumentUsable = \(doc\) =>/);
  assert.match(themeManager, /-webkit-user-select:\s*text;/);
  assert.match(themeManager, /body,\s*body \*/);
  assert.doesNotMatch(themeManager, /div \{ margin-right: 0 !important;/);
});

test("fullscreen resize lifecycle no longer cancels completion callbacks", () => {
  const readerApp = readProjectFile("static/js/reader/reader-application.js");
  assert.match(readerApp, /clearViewportResizeWork\(\)/);
  assert.match(readerApp, /clearFullscreenResizeTimers\(\)/);
  assert.match(readerApp, /stabilizeViewportResize[\s\S]*this\.clearFullscreenResizeTimers\(\);/);
  assert.match(readerApp, /resizeReaderViewport[\s\S]*this\.clearViewportResizeWork\(\);/);
});

test("runtime managers avoid unload listeners in restricted contexts", () => {
  const renderingEngine = readProjectFile(
    "static/js/vendor/epub-runtime/modules/rendering-engine.modules.js"
  );
  const navigationEngine = readProjectFile(
    "static/js/vendor/epub-runtime/modules/navigation-engine.modules.js"
  );
  assert.match(renderingEngine, /addEventListener\("pagehide"/);
  assert.match(navigationEngine, /addEventListener\("pagehide"/);
  assert.doesNotMatch(renderingEngine, /addEventListener\(\s*"unload"/);
  assert.doesNotMatch(navigationEngine, /addEventListener\(\s*"unload"/);
});

test("service worker cache lookup respects query-string variants", () => {
  const serviceWorker = readProjectFile("service-worker.js");
  assert.match(serviceWorker, /caches\.match\(request,\s*\{\s*ignoreSearch:\s*false\s*\}\)/);
  assert.match(serviceWorker, /if \(requestURL\.search\)\s*\{\s*return null;\s*\}/);
});

test("reader supports backend launch manifests and remote reading-state sync", () => {
  const readerApp = readProjectFile("static/js/reader/reader-application.js");
  assert.match(readerApp, /getLaunchManifestUrl\(\)/);
  assert.match(readerApp, /loadManifestLaunchIfPresent\(\)/);
  assert.match(readerApp, /manifest\.epub_download_url/);
  assert.match(readerApp, /reading_session_url/);
  assert.match(readerApp, /queueReadingStateSync\(location\)/);
  assert.match(readerApp, /fetch\(syncUrl,\s*\{/);
});
