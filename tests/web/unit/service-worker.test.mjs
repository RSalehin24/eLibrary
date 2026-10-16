import assert from "node:assert/strict";
import { test } from "node:test";
import { configureWorker } from "../../../app/web/src/pwa/service-worker.mjs";

const configuration = { cache: "library-static-current", assets: ["/_next/static/chunk.abc.js", "/offline.fingerprint.html"], offline: "/offline.fingerprint.html" };

class WorkerScope {
  location = { origin: "https://library.test" };
  handlers = new Map();
  stored = new Map();
  requested = [];
  activated = false;
  claimed = false;
  clients = { claim: async () => { this.claimed = true; } };
  caches = {
    open: async (name) => {
      if (!this.stored.has(name)) this.stored.set(name, new Map());
      const contents = this.stored.get(name);
      return { addAll: async (requests) => { for (const request of requests) { this.requested.push(request); contents.set(request.url, new Response(request.url.includes("offline") ? "সংযোগ প্রয়োজন" : "code")); } }, match: async (request) => contents.get(new URL(typeof request === "string" ? request : request.url, this.location.origin).href)?.clone() };
    },
    keys: async () => Array.from(this.stored.keys()),
    delete: async (name) => this.stored.delete(name),
  };
  fetch = async () => new Response("online");
  addEventListener(type, callback) { this.handlers.set(type, callback); }
  skipWaiting() { this.activated = true; }
  dispatch(type, fields = {}) {
    let response;
    this.handlers.get(type)({ ...fields, waitUntil: (value) => { response = value; }, respondWith: (value) => { response = value; } });
    return response;
  }
}

function worker() { const scope = new WorkerScope(); configureWorker(scope, configuration); return scope; }
function request(path, options = {}) { return { url: `https://library.test${path}`, method: "GET", mode: "cors", destination: "", ...options }; }

test("precache contains only the explicit static allowlist without credentials", async () => {
  const scope = worker(); await scope.dispatch("install");
  assert.deepEqual(scope.requested.map((entry) => entry.url), configuration.assets.map((path) => `https://library.test${path}`));
  assert.ok(scope.requested.every((entry) => entry.credentials === "omit"));
  assert.equal(scope.activated, false);
});

test("private APIs, mutations, reader documents and navigation payloads bypass caching", async () => {
  const scope = worker(); await scope.dispatch("install");
  for (const entry of [request("/api/v1/auth/session/"), request("/api/v1/reading/sessions/uuid/resources/chapter.xhtml", { mode: "navigate", destination: "iframe" }), request("/notes/?_rsc=private"), request("/_next/static/chunk.abc.js?token=private"), request("/_next/static/chunk.abc.js", { method: "POST" })]) assert.equal(scope.dispatch("fetch", { request: entry }), undefined);
  assert.equal((await scope.dispatch("fetch", { request: request("/_next/static/chunk.abc.js") })).status, 200);
});

test("document network failures show the generic fallback without storing private HTML", async () => {
  const scope = worker(); await scope.dispatch("install");
  scope.fetch = async () => { throw new TypeError("offline"); };
  const response = await scope.dispatch("fetch", { request: request("/reader/private-session/", { mode: "navigate", destination: "document" }) });
  assert.equal(await response.text(), "সংযোগ প্রয়োজন");
  assert.equal(scope.stored.get(configuration.cache).size, 2);
});

test("real HTTP errors are preserved without offline substitution", async () => {
  const scope = worker(); await scope.dispatch("install");
  scope.fetch = async () => new Response("real server failure", { status: 503 });
  const response = await scope.dispatch("fetch", { request: request("/", { mode: "navigate", destination: "document" }) });
  assert.equal(response.status, 503);
  assert.equal(await response.text(), "real server failure");
});

test("updates activate only on acceptance and retain two previous application caches", async () => {
  const scope = worker();
  for (const name of ["other-app", "library-static-first", "library-static-second", "library-static-third", configuration.cache]) await scope.caches.open(name);
  scope.dispatch("message", { data: { type: "unrelated" } }); assert.equal(scope.activated, false);
  scope.dispatch("message", { data: { type: "ACCEPT_UPDATE" } }); assert.equal(scope.activated, true);
  await scope.dispatch("activate");
  assert.deepEqual(await scope.caches.keys(), ["other-app", "library-static-second", "library-static-third", configuration.cache]);
  assert.equal(scope.claimed, true);
});
