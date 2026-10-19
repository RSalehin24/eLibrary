import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { bookmarkTextLocation, parseBookmarkTextLocation, bookmarkPositionAtOffset } = await typescriptModule(new URL("../../../app/web/src/lib/bookmark-text-position.ts", import.meta.url));
const { initialPosition } = await typescriptModule(new URL("../../../app/web/src/lib/reading-position.ts", import.meta.url));
const { bookmarkTextRange } = await typescriptModule(new URL("../../../app/web/src/lib/bookmark-text-anchor.ts", import.meta.url));

test("persistent bookmark anchors retain UTF-16 offsets and literal Bengali, emoji and escaped quote text", () => {
  const position = { chapter: 1, offset: 123, quote: 'বাংলা 🪷 "একটি" \\ জায়গা' };
  const location = bookmarkTextLocation(position);
  assert.deepEqual(parseBookmarkTextLocation(location), position);
  assert.deepEqual(initialPosition({ last_location: location, progress_percent: 0 }, 2), { chapter: 1, offset: 0, textAnchor: position });
  assert.equal(initialPosition({ last_location: location, progress_percent: 0 }, 1).restoration, "missing");
});

test("anchor input rejects invalid offsets, extra fields, missing quotes and unsupported lengths", () => {
  for (const value of [null, [], {}, { chapter: 0, offset: 1, quote: " " }, { chapter: 1.5, offset: 1, quote: "word" }, { chapter: 0, offset: 32_000_001, quote: "word" }, { chapter: 0, offset: 1, quote: "ক".repeat(33) }, { chapter: 0, offset: 1, quote: "word", extra: true }]) {
    assert.equal(parseBookmarkTextLocation("text:" + JSON.stringify(value)), null);
  }
});

test("bookmark capture advances past invisible inter-paragraph whitespace without changing UTF-16 text offsets", () => {
  assert.deepEqual(bookmarkPositionAtOffset("🪷 \n    বাংলা পাঠকের", 1, 3), { chapter: 1, offset: 8, quote: "বাংলা পাঠকের" });
  assert.deepEqual(bookmarkPositionAtOffset("  " + "a".repeat(31) + " next", 0, 0), { chapter: 0, offset: 2, quote: "a".repeat(31) });
  const empty = bookmarkPositionAtOffset(" \n ", 0, 0);
  assert.equal(bookmarkTextLocation(empty), null);
});

function documentWithText(text) {
  const node = { nodeType: 3, length: text.length, textContent: text };
  let visited = false;
  return {
    body: {}, createTreeWalker: () => ({ nextNode: () => visited ? null : (visited = true, node) }),
    createRange: () => ({ start: 0, end: 0, setStart(_, offset) { this.start = offset; }, setEnd(_, offset) { this.end = offset; }, toString() { return text.slice(this.start, this.end); }, collapse() { this.end = this.start; } }),
  };
}

test("restoration verifies the exact quotation before creating a collapsed passage range", () => {
  const previous = globalThis.NodeFilter;
  globalThis.NodeFilter = { SHOW_TEXT: 4, SHOW_CDATA_SECTION: 8 };
  try {
    const anchor = { chapter: 0, offset: 3, quote: "বাংলা" };
    const document = documentWithText("🪷 বাংলা পরে"); document.body.ownerDocument = document;
    assert.equal(bookmarkTextRange(document, anchor).start, 3);
    const changed = documentWithText("🪷 অন্য পরে"); changed.body.ownerDocument = changed;
    assert.equal(bookmarkTextRange(changed, anchor), null);
    const missing = documentWithText("short"); missing.body.ownerDocument = missing;
    assert.equal(bookmarkTextRange(missing, { ...anchor, offset: 99 }), null);
  } finally { if (previous) globalThis.NodeFilter = previous; else delete globalThis.NodeFilter; }
});
