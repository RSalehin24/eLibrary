export function configureWorker(scope, configuration) {
  const allowed = new Set(configuration.assets.map((path) => new URL(path, scope.location.origin).href));
  scope.addEventListener("install", (event) => event.waitUntil(precache(scope, configuration)));
  scope.addEventListener("activate", (event) => event.waitUntil(activate(scope, configuration.cache)));
  scope.addEventListener("message", (event) => { if (event.data?.type === "ACCEPT_UPDATE") scope.skipWaiting(); });
  scope.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") return;
    if (request.mode === "navigate" && request.destination === "document") { event.respondWith(navigate(scope, request, configuration)); return; }
    if (allowed.has(request.url)) event.respondWith(staticAsset(scope, request, configuration.cache));
  });
}

async function precache(scope, configuration) {
  const cache = await scope.caches.open(configuration.cache);
  await cache.addAll(configuration.assets.map((path) => new Request(new URL(path, scope.location.origin), { credentials: "omit", cache: "reload" })));
}

async function activate(scope, currentCache) {
  const caches = (await scope.caches.keys()).filter((name) => name.startsWith("library-static-"));
  const previous = caches.filter((name) => name !== currentCache);
  await Promise.all(previous.slice(0, -2).map((name) => scope.caches.delete(name)));
  await scope.clients.claim();
}

async function navigate(scope, request, configuration) {
  try { return await scope.fetch(request); }
  catch {
    const path = new URL(request.url).pathname === "/local-reader/" && configuration.localReader ? configuration.localReader : configuration.offline;
    const fallback = await (await scope.caches.open(configuration.cache)).match(path);
    return fallback ?? new Response("ইন্টারনেট সংযোগ প্রয়োজন।", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}

async function staticAsset(scope, request, cacheName) {
  const cache = await scope.caches.open(cacheName);
  const cached = await cache.match(request);
  return cached ?? scope.fetch(request);
}
