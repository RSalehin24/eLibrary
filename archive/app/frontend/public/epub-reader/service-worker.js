const CACHE_NAME = "epub-reader-v6";

const READER_SCRIPT_FILES = [
  "./static/js/app/pwa.js",
  "./static/js/app/boot-reader.js",
  "./static/js/reader/reader-settings.js",
  "./static/js/reader/reader-application.js",
  "./static/js/reader/utils/dom-helpers.js",
  "./static/js/reader/utils/toc-helpers.js",
  "./static/js/reader/utils/gesture-handlers.js",
  "./static/js/reader/controllers/loading-indicator-controller.js",
  "./static/js/reader/controllers/theme-manager.js",
  "./static/js/reader/controllers/shortcut-dialog-controller.js",
  "./static/js/reader/controllers/iframe-bridge-controller.js",
  "./static/js/reader/controllers/settings-panel-controller.js"
];

const EPUB_RUNTIME_FILES = [
  "./static/js/vendor/epub-runtime/runtime-entry.js",
  "./static/js/vendor/epub-runtime/module-loader.js",
  "./static/js/vendor/epub-runtime/modules/core-utilities.modules.js",
  "./static/js/vendor/epub-runtime/modules/rendering-engine.modules.js",
  "./static/js/vendor/epub-runtime/modules/content-parsers.modules.js",
  "./static/js/vendor/epub-runtime/modules/navigation-engine.modules.js",
  "./static/js/vendor/epub-runtime/modules/archive-loading.modules.js",
  "./static/js/vendor/epub-runtime/modules/compatibility-shims.modules.js",
  "./static/js/vendor/epub-runtime/modules/binary-helpers.modules.js",
  "./static/js/vendor/epub-runtime/modules/async-scheduling.modules.js"
];

const APP_SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./static/css/base/reset.css",
  "./static/css/base/iconfont.css",
  "./static/css/base/helpers.css",
  "./static/css/components/shortcuts-dialog.css",
  "./static/css/components/landing-screen.css",
  "./static/css/components/reader-layout.css",
  "./static/css/themes/theme-tokens.css",
  "./static/css/themes/theme-overrides.css",
  ...READER_SCRIPT_FILES,
  ...EPUB_RUNTIME_FILES,
  "./static/img/book.svg",
  "./static/img/favicon.png",
  "./static/img/icon-192.png",
  "./static/img/icon-512.png"
];

const NETWORK_FIRST_EXTENSIONS = [".html", ".js", ".css", ".webmanifest"];

function isCacheableResponse(response) {
  return !!response && response.status === 200;
}

function shouldHandleRequest(request, requestURL) {
  if (request.method !== "GET") return false;
  if (!/^https?:$/.test(requestURL.protocol)) return false;
  if (requestURL.origin !== self.location.origin) return false;
  if (request.cache === "only-if-cached" && request.mode !== "same-origin") return false;
  return true;
}

function shouldUseNetworkFirst(request, requestURL) {
  if (request.mode === "navigate") return true;
  return NETWORK_FIRST_EXTENSIONS.some((extension) =>
    requestURL.pathname.endsWith(extension)
  );
}

async function putInCache(request, response) {
  if (!isCacheableResponse(response)) return;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
}

async function matchFromCache(request) {
  const exactMatch = await caches.match(request, { ignoreSearch: false });
  if (exactMatch) return exactMatch;

  const requestURL = new URL(request.url);

  if (request.mode === "navigate") {
    const normalizedPath = requestURL.pathname.startsWith("/")
      ? `.${requestURL.pathname}`
      : requestURL.pathname;
    const pathMatch =
      (await caches.match(requestURL.pathname, { ignoreSearch: true })) ||
      (await caches.match(normalizedPath, { ignoreSearch: true }));
    if (pathMatch) return pathMatch;
    return caches.match("./index.html");
  }

  if (requestURL.search) {
    return null;
  }

  const normalizedPath = requestURL.pathname.startsWith("/")
    ? `.${requestURL.pathname}`
    : requestURL.pathname;
  const pathMatch =
    (await caches.match(requestURL.pathname, { ignoreSearch: false })) ||
    (await caches.match(normalizedPath, { ignoreSearch: false }));
  if (pathMatch) return pathMatch;

  return null;
}

async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (isCacheableResponse(networkResponse)) {
      putInCache(request, networkResponse).catch(() => {
        // Ignore cache write errors and keep request successful.
      });
    }
    return networkResponse;
  } catch {
    const cachedResponse = await matchFromCache(request);
    if (cachedResponse) return cachedResponse;

    if (request.mode === "navigate") {
      const fallback = await caches.match("./index.html");
      if (fallback) return fallback;
    }

    return new Response("Offline", {
      status: 503,
      statusText: "Offline"
    });
  }
}

async function cacheFirst(request) {
  const cachedResponse = await matchFromCache(request);
  if (cachedResponse) return cachedResponse;

  try {
    const networkResponse = await fetch(request);
    if (isCacheableResponse(networkResponse)) {
      putInCache(request, networkResponse).catch(() => {
        // Ignore cache write errors and keep request successful.
      });
    }
    return networkResponse;
  } catch {
    if (request.mode === "navigate") {
      const fallback = await caches.match("./index.html");
      if (fallback) return fallback;
    }

    return new Response("Offline", {
      status: 503,
      statusText: "Offline"
    });
  }
}

async function preCacheAppShell() {
  const cache = await caches.open(CACHE_NAME);

  await Promise.allSettled(
    APP_SHELL_FILES.map(async (assetPath) => {
      const response = await fetch(assetPath, { cache: "no-cache" });
      if (!isCacheableResponse(response)) return;
      await cache.put(assetPath, response.clone());
    })
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(preCacheAppShell());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => caches.delete(cacheName))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const requestURL = new URL(event.request.url);
  if (!shouldHandleRequest(event.request, requestURL)) return;

  if (shouldUseNetworkFirst(event.request, requestURL)) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  event.respondWith(cacheFirst(event.request));
});
