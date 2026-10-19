import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { jumpToRange } = await typescriptModule(new URL("../../../app/web/src/lib/reader-annotations.ts", import.meta.url));

function context(view = "scroll") {
  const root = { scrollTop: 10, scrollLeft: 0, clientHeight: 600, clientWidth: 400, dataset: { readerView: view } };
  return { root, document: { scrollingElement: root, documentElement: root, getSelection: () => null } };
}

test("collapsed element CFI points scroll to the proven element when the range has no text rectangle", () => {
  const { root, document } = context();
  const element = { nodeType: 1, getBoundingClientRect: () => ({ top: 1200, left: 0 }) };
  const range = { startContainer: element, collapsed: true, getClientRects: () => [] };
  assert.equal(jumpToRange(document, range), true);
  assert.equal(root.scrollTop, 1010);
});

test("element CFI points navigate to the correct page without inventing a text selection", () => {
  const { root, document } = context("single");
  const element = { nodeType: 1, getBoundingClientRect: () => ({ top: 0, left: 1250 }) };
  assert.equal(jumpToRange(document, { startContainer: element, collapsed: true, getClientRects: () => [] }), true);
  assert.equal(root.scrollLeft, 1200);
});

test("unresolvable text ranges fail explicitly and do not move the reader", () => {
  const { root, document } = context();
  const range = { startContainer: { nodeType: 3, parentElement: {} }, collapsed: true, getClientRects: () => [] };
  assert.equal(jumpToRange(document, range), false);
  assert.equal(root.scrollTop, 10);
  const hidden = { nodeType: 1, getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }) };
  assert.equal(jumpToRange(document, { ...range, startContainer: hidden }), false);
  assert.equal(root.scrollTop, 10);
});
