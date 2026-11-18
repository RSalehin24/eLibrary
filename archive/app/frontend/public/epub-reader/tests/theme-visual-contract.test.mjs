import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function readProjectFile(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), "utf8");
}

test("theme tokens include reader surface and nav icon variables", () => {
  const tokens = readProjectFile("static/css/themes/theme-tokens.css");
  assert.match(tokens, /body\.epub-container,\s*\.reader-page-fullscreen\.epub-container\s*\{/);
  assert.match(tokens, /--reader-page-surface:/);
  assert.match(tokens, /--reader-shell-border:/);
  assert.match(tokens, /--reader-surface-bg:/);
  assert.match(tokens, /--nav-icon-bg-top:/);
  assert.match(tokens, /--nav-icon-color:/);
  assert.doesNotMatch(tokens, /^\s*\.epub-container\s*\{$/m);
});

test("theme tokens do not contain deprecated close-specific overrides", () => {
  const tokens = readProjectFile("static/css/themes/theme-tokens.css");
  assert.doesNotMatch(tokens, /--nav-close-/);
});

test("theme overrides keep wrapper-main as background host and epub viewport transparent", () => {
  const overrides = readProjectFile("static/css/themes/theme-overrides.css");
  assert.match(overrides, /\.wrapper-main\s*\{\s*background:\s*var\(--reader-background,\s*var\(--page-background\)\);/);
  assert.match(overrides, /\.reader-wrapper-container\s*\{\s*background:\s*transparent\s*!important;/);
  assert.match(overrides, /\[id\^="epubjs-container-"\]\s*\{[\s\S]*background:\s*transparent\s*!important;/);
  assert.match(
    overrides,
    /\.epub-container,\s*[\s\S]*\[id\^="epubjs-container-"\]\s*\{\s*scrollbar-color:\s*var\(--scrollbar-thumb\)\s*var\(--scrollbar-track\);/
  );
  assert.doesNotMatch(overrides, /body\.epub-container/);
});

test("navigation icons are inline SVG based", () => {
  const html = readProjectFile("index.html");
  assert.match(html, /class="iconfont"[^>]*>\s*<svg/);
  assert.doesNotMatch(html, /aria-label="Close current book"/);
});

test("iframe theme manager injects themed scrollbar styles", () => {
  const themeManager = readProjectFile("static/js/reader/controllers/theme-manager.js");
  assert.match(themeManager, /const scrollbarPaletteByTheme = \{/);
  assert.match(themeManager, /scrollbar-color:\s*\$\{scrollbarThumb\}\s*\$\{scrollbarTrack\};/);
  assert.match(themeManager, /\.reader-scroll-container::-webkit-scrollbar-thumb \{/);
});
