import assert from "node:assert/strict";
import test from "node:test";

import {
  buildBookReaderLocation,
  launchBookReader,
} from "../../../app/frontend/src/features/book-detail/readerLaunch.js";

test("buildBookReaderLocation keeps the book slug and manifest in the reader url", () => {
  assert.equal(
    buildBookReaderLocation(
      {
        manifest_url: "http://testserver/api/access/reader/token-123/manifest/",
      },
      "preview-book",
    ),
    "/reader?slug=preview-book&manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-123%2Fmanifest%2F&appNav=hidden",
  );
});

test("buildBookReaderLocation falls back to the launch url manifest", () => {
  assert.equal(
    buildBookReaderLocation(
      {
        launch_url:
          "http://frontend.test/reader?manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-456%2Fmanifest%2F",
      },
      "detail-book",
    ),
    "/reader?slug=detail-book&manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-456%2Fmanifest%2F&appNav=hidden",
  );
});

test("launchBookReader calls reader-launch and navigates with the resolved reader url", async () => {
  let request = null;
  const navigated = [];

  await launchBookReader({
    slug: "detail-book",
    apiClient: async (path, options) => {
      request = { path, options };
      return {
        manifest_url: "http://testserver/api/access/reader/token-789/manifest/",
      };
    },
    navigate: (url) => {
      navigated.push(url);
    },
  });

  assert.deepEqual(request, {
    path: "/access/books/detail-book/reader-launch/",
    options: {
      method: "POST",
      body: {},
    },
  });
  assert.deepEqual(navigated, [
    "/reader?slug=detail-book&manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-789%2Fmanifest%2F&appNav=hidden",
  ]);
});
