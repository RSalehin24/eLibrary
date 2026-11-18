import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeReaderManifestPayload,
  resolveReaderManifestUrl,
} from "../../../app/frontend/src/features/reader/manifest.js";

function normalizeToBrowserOrigin(value) {
  return value.replace("http://testserver", "http://127.0.0.1:5173");
}

test("resolveReaderManifestUrl extracts and normalizes a manifest from launch_url", () => {
  assert.equal(
    resolveReaderManifestUrl(
      {
        launch_url:
          "http://frontend.test/reader?manifest=http%3A%2F%2Ftestserver%2Fapi%2Faccess%2Freader%2Ftoken-789%2Fmanifest%2F",
      },
      normalizeToBrowserOrigin,
    ),
    "http://127.0.0.1:5173/api/access/reader/token-789/manifest/",
  );
});

test("normalizeReaderManifestPayload normalizes browser-facing manifest urls", () => {
  assert.deepEqual(
    normalizeReaderManifestPayload(
      {
        epub_download_url: "http://testserver/api/access/reader/token-789/epub/",
        html_preview_url: "http://testserver/api/access/reader/token-789/html/",
        reading_session_url: "http://testserver/api/access/reader/token-789/session/",
        bookmarks_url: "http://testserver/api/access/reader/token-789/bookmarks/",
      },
      normalizeToBrowserOrigin,
    ),
    {
      epub_download_url: "http://127.0.0.1:5173/api/access/reader/token-789/epub/",
      html_preview_url: "http://127.0.0.1:5173/api/access/reader/token-789/html/",
      reading_session_url: "http://127.0.0.1:5173/api/access/reader/token-789/session/",
      bookmarks_url: "http://127.0.0.1:5173/api/access/reader/token-789/bookmarks/",
    },
  );
});
