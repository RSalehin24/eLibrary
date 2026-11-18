import test from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, normalize, extname } from "node:path";

const PROJECT_ROOT = resolve(process.cwd());

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon"
};

let chromium = null;
try {
  ({ chromium } = await import("playwright"));
} catch {
  chromium = null;
}

function createStaticServer(rootDir) {
  return createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url || "/", "http://localhost");
      const pathname = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
      const safeRelativePath = normalize(pathname).replace(/^([.][.][/\\])+/, "");
      const absolutePath = resolve(rootDir, `.${safeRelativePath.startsWith("/") ? safeRelativePath : `/${safeRelativePath}`}`);

      if (!absolutePath.startsWith(rootDir)) {
        response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
        response.end("Forbidden");
        return;
      }

      const fileContent = await readFile(absolutePath);
      const contentType = CONTENT_TYPES[extname(absolutePath)] || "application/octet-stream";
      response.writeHead(200, { "Content-Type": contentType });
      response.end(fileContent);
    } catch {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not Found");
    }
  });
}

async function runInBrowser(testContext, runScenario) {
  if (!chromium) {
    testContext.skip("playwright is not installed in this environment");
    return;
  }

  const server = createStaticServer(PROJECT_ROOT);
  await new Promise((resolvePromise) => server.listen(0, resolvePromise));

  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  const baseUrl = `http://127.0.0.1:${port}`;

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch {
    await new Promise((resolvePromise) => server.close(resolvePromise));
    testContext.skip("playwright browser runtime is unavailable");
    return;
  }

  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();

  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.waitForFunction(() => !!window.__epubReaderApp, null, { timeout: 10000 });
    await runScenario(page);
  } finally {
    await context.close();
    await browser.close();
    await new Promise((resolvePromise) => server.close(resolvePromise));
  }
}

test("playwright smoke: compact TOC rail keeps non-primary controls hidden", async (t) => {
  await runInBrowser(t, async (page) => {
    const state = await page.evaluate(() => {
      const openPage = document.querySelector(".open-ebook-page");
      const reader = document.querySelector(".epub-reader-container");
      const toc = document.querySelector(".epub-contents");

      if (openPage) openPage.style.display = "none";
      if (reader) reader.style.display = "flex";
      toc?.classList.remove("close");

      const wrapperNav = document.querySelector(".reader-wrapper .wrapper-nav");
      const wrapperMain = document.querySelector(".reader-wrapper .wrapper-main");
      const settingsAnchor = wrapperNav?.querySelector(".icon-anchor");
      const tocToggle = wrapperNav?.querySelector(".iconmulu");

      return {
        wrapperMainVisibility: wrapperMain ? getComputedStyle(wrapperMain).visibility : "",
        wrapperMainPointerEvents: wrapperMain ? getComputedStyle(wrapperMain).pointerEvents : "",
        settingsDisplay: settingsAnchor ? getComputedStyle(settingsAnchor).display : "",
        tocToggleDisplay: tocToggle ? getComputedStyle(tocToggle).display : "",
        wrapperNavJustifyContent: wrapperNav ? getComputedStyle(wrapperNav).justifyContent : ""
      };
    });

    assert.equal(state.wrapperMainVisibility, "hidden");
    assert.equal(state.wrapperMainPointerEvents, "none");
    assert.equal(state.settingsDisplay, "none");
    assert.equal(state.tocToggleDisplay, "flex");
    assert.equal(state.wrapperNavJustifyContent, "flex-end");
  });
});

test("playwright smoke: immersive mode keeps padding and clears loading state", async (t) => {
  await runInBrowser(t, async (page) => {
    await page.evaluate(() => {
      const openPage = document.querySelector(".open-ebook-page");
      const reader = document.querySelector(".epub-reader-container");
      if (openPage) openPage.style.display = "none";
      if (reader) reader.style.display = "flex";

      const app = window.__epubReaderApp;
      app.rendition = {
        resize() {},
        getContents() {
          return [];
        }
      };

      app.iframeBridgeController.waitForContentReady = (onDone) => {
        if (typeof onDone === "function") {
          setTimeout(() => onDone(null), 10);
        }
        return Promise.resolve(null);
      };

      app.toggleImmersiveMode(true);
    });

    await page.waitForTimeout(1200);

    const immersiveState = await page.evaluate(() => {
      const readerContainer = document.querySelector(".epub-reader-container");
      const wrapperMain = document.querySelector(".reader-wrapper .wrapper-main");
      const viewer = document.querySelector("#viewer");

      return {
        immersiveOn: !!readerContainer?.classList.contains("immersive-reading"),
        viewerLoading: !!viewer?.classList.contains("loading"),
        wrapperMainPaddingTop: wrapperMain ? parseFloat(getComputedStyle(wrapperMain).paddingTop) : 0,
        containerPaddingTop: readerContainer
          ? parseFloat(getComputedStyle(readerContainer).paddingTop)
          : 0
      };
    });

    assert.equal(immersiveState.immersiveOn, true);
    assert.equal(immersiveState.viewerLoading, false);
    assert.ok(immersiveState.wrapperMainPaddingTop >= 6);
    assert.ok(immersiveState.containerPaddingTop >= 6);
  });
});

test("playwright smoke: iframe theme overrides are scoped and selection-friendly", async (t) => {
  await runInBrowser(t, async (page) => {
    const themeStyles = await page.evaluate(async () => {
      const app = window.__epubReaderApp;
      const viewer = document.querySelector("#viewer");
      if (!viewer) return null;

      viewer.innerHTML =
        '<iframe id="smoke-frame" srcdoc="<!doctype html><html><body><div style=\"margin:24px\">Smoke test paragraph</div></body></html>"></iframe>';

      const iframe = document.getElementById("smoke-frame");
      if (!iframe) return null;

      await new Promise((resolvePromise) => {
        iframe.addEventListener("load", () => resolvePromise(), { once: true });
      });

      const doc = iframe.contentDocument;
      if (!doc) return null;

      app.readerThemeManager.applyThemeToCurrentPage(0, {
        getContents() {
          return [{ document: doc }];
        }
      });

      return {
        mobileReset: doc.getElementById("epub-mobile-reset")?.textContent || "",
        themeOverrides: doc.getElementById("epub-theme-overrides")?.textContent || ""
      };
    });

    assert.ok(themeStyles);
    assert.doesNotMatch(themeStyles.mobileReset, /div\s*\{/);
    assert.match(themeStyles.themeOverrides, /user-select:\s*text/);
    assert.match(themeStyles.themeOverrides, /body,\s*body \*/);
  });
});
