import assert from "node:assert/strict";
import test from "node:test";

import {
  resolveApiUrl,
} from "../../../app/frontend/src/api/urls.js";
import { normalizeAppUrl } from "../../../app/frontend/src/api/urlNormalization.js";

test("normalizeAppUrl rewrites absolute API urls onto the current origin", () => {
  assert.equal(
    normalizeAppUrl("http://testserver/api/access/reader/token-123/manifest/", {
      currentOrigin: "http://127.0.0.1:5173",
      apiBaseUrl: "/api",
    }),
    "http://127.0.0.1:5173/api/access/reader/token-123/manifest/",
  );
});

test("normalizeAppUrl rewrites nested manifest urls inside launch urls", () => {
  assert.equal(
    normalizeAppUrl(
      "http://frontend.test/reader?manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-456%2Fmanifest%2F",
      {
        currentOrigin: "http://127.0.0.1:5173",
        apiBaseUrl: "/api",
      },
    ),
    "http://frontend.test/reader?manifest=http%3A%2F%2F127.0.0.1%3A5173%2Fapi%2Faccess%2Freader%2Ftoken-456%2Fmanifest%2F",
  );
});

test("resolveApiUrl prefixes relative backend paths with the api base path", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    location: {
      origin: "http://127.0.0.1:5173",
    },
  };

  try {
    assert.equal(
      resolveApiUrl("/processing/stream/"),
      "http://127.0.0.1:5173/api/processing/stream/",
    );
  } finally {
    globalThis.window = originalWindow;
  }
});
