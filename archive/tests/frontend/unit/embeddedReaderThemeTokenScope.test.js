import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(currentFile), "..", "..", "..");

test("embedded reader theme tokens scope variables to the host container only", () => {
  const tokens = fs.readFileSync(
    path.join(
      repoRoot,
      "app/frontend/src/embedded-reader/static/css/themes/theme-tokens.css",
    ),
    "utf8",
  );

  assert.match(
    tokens,
    /body\.epub-container,\s*\.reader-page-fullscreen\.epub-container\s*\{/,
  );
  assert.match(
    tokens,
    /body\.epub-container\.theme-type-1,\s*\.reader-page-fullscreen\.epub-container\.theme-type-1\s*\{/,
  );
  assert.match(
    tokens,
    /body\.epub-container\.theme-type-2,\s*\.reader-page-fullscreen\.epub-container\.theme-type-2\s*\{/,
  );
  assert.doesNotMatch(tokens, /^\s*\.epub-container\s*\{$/m);
});
