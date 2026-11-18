import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..", "..", "..");

test("embedded reader scrollbar theming targets the mounted epub container instead of body only", () => {
  const overrides = fs.readFileSync(
    path.join(
      repoRoot,
      "app/frontend/src/embedded-reader/static/css/themes/theme-overrides.css",
    ),
    "utf8",
  );

  assert.match(overrides, /^\.epub-container,\s*$/m);
  assert.match(
    overrides,
    /\.epub-container \.epub-reader-container \.epub-contents,\s*[\s\S]*scrollbar-color:\s*var\(--scrollbar-thumb\)\s*var\(--scrollbar-track\);/,
  );
  assert.doesNotMatch(overrides, /body\.epub-container/);
});
