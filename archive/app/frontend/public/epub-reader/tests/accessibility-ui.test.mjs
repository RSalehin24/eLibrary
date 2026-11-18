import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function readProjectFile(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), "utf8");
}

test("landing primary action is a semantic button", () => {
  const html = readProjectFile("index.html");
  assert.match(
    html,
    /<button[^>]*id="open-new-book"[^>]*class="[^"]*open-ebook-btn[^"]*"[^>]*>/i
  );
});

test("layout includes a keyboard skip link", () => {
  const html = readProjectFile("index.html");
  assert.match(
    html,
    /<a[^>]*class="skip-link"[^>]*href="#reader-controls"[^>]*>/i
  );
});

test("reader nav controls expose aria labels and button semantics", () => {
  const html = readProjectFile("index.html");

  assert.match(
    html,
    /<button[^>]*class="[^"]*icon-wrap[^"]*iconmulu[^"]*"[^>]*aria-label="Toggle table of contents"[^>]*>/i
  );
  assert.match(
    html,
    /<button[^>]*class="[^"]*icon-control[^"]*iconshezhi[^"]*"[^>]*aria-label="Open reading settings"[^>]*>/i
  );
  assert.match(
    html,
    /<button[^>]*class="[^"]*arrow[^"]*prev-btn[^"]*"[^>]*aria-label="Previous section"[^>]*>/i
  );
  assert.match(
    html,
    /<button[^>]*class="[^"]*arrow[^"]*next-btn[^"]*"[^>]*aria-label="Next section"[^>]*>/i
  );
  assert.doesNotMatch(html, /aria-label="Close current book"/i);
});

test("toc and settings controls are wired with aria relationships", () => {
  const html = readProjectFile("index.html");

  assert.match(html, /id="epub-contents-panel"/i);
  assert.match(html, /id="reader-settings-panel"/i);
  assert.match(
    html,
    /class="[^"]*iconmulu[^"]*"[^>]*aria-controls="epub-contents-panel"[^>]*aria-expanded="false"/i
  );
  assert.match(
    html,
    /class="[^"]*iconshezhi[^"]*"[^>]*aria-haspopup="true"[^>]*aria-controls="reader-settings-panel"[^>]*aria-expanded="false"/i
  );
  assert.match(
    html,
    /id="reader-settings-panel"[^>]*role="group"[^>]*aria-label="Reading settings"[^>]*aria-hidden="true"/i
  );
  assert.match(
    html,
    /class="[^"]*bg-btn[^"]*"[^>]*data-type="0"[^>]*aria-pressed="true"/i
  );
});

test("toc helper renders semantic button rows", () => {
  const tocHelper = readProjectFile("static/js/reader/utils/toc-helpers.js");
  assert.match(tocHelper, /<button type="button" class="slide-contents-item-label/i);
  assert.doesNotMatch(tocHelper, /role="button"/i);
});

test("reader app and settings controller synchronize aria-expanded state", () => {
  const readerApp = readProjectFile("static/js/reader/reader-application.js");
  const settingsController = readProjectFile(
    "static/js/reader/controllers/settings-panel-controller.js"
  );

  assert.match(readerApp, /syncTocToggleAriaState\(\)/);
  assert.match(readerApp, /toggleButton\.setAttribute\("aria-expanded"/);
  assert.match(settingsController, /syncTriggerAriaExpanded\(isExpanded\)/);
  assert.match(settingsController, /trigger\.setAttribute\("aria-expanded"/);
  assert.match(settingsController, /panelElement\.setAttribute\("aria-hidden", "false"\)/);
  assert.match(settingsController, /panelElement\.setAttribute\("aria-hidden", "true"\)/);
  assert.match(readerApp, /syncThemeControlState\(\)/);
  assert.match(readerApp, /syncFontControlState\(\)/);
  assert.match(readerApp, /button\.setAttribute\("aria-pressed", isActive \? "true" : "false"\)/);
  assert.match(readerApp, /button\.disabled = isDisabled/);
});
