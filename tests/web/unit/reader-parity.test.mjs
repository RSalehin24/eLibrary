import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";
const { checkedReaderAppearance, readerAppearanceShortcut } = await typescriptModule(new URL("../../../app/web/src/lib/reader-preferences.ts", import.meta.url));
const { readerPageState, turnReaderPage, readerKeyboardDirection } = await typescriptModule(new URL("../../../app/web/src/lib/reader-pagination.ts", import.meta.url));
const { scrollFraction, restoreScroll } = await typescriptModule(new URL("../../../app/web/src/lib/reader-document.ts", import.meta.url));
const { chapterMatches } = await typescriptModule(new URL("../../../app/web/src/lib/reader-search.ts", import.meta.url));

test("reader preferences validate persisted values and keep supported reading views", () => {
  assert.equal(checkedReaderAppearance(null).fontSize, 20);
  assert.equal(checkedReaderAppearance({ fontSize: Infinity, theme: "invalid", view: "script", font: "url(x)" }).fontSize, 20);
  assert.deepEqual(checkedReaderAppearance({ fontSize: 90, theme: "dark", view: "spread", font: "sans", lineHeight: 10, width: 1040 }), { fontSize: 40, theme: "dark", view: "spread", font: "sans", lineHeight: 2.4, width: 1040 });
  assert.equal(checkedReaderAppearance({ fontSize: -10 }).fontSize, 14);
});

test("original reader theme and text shortcuts validate bounds and preserve editing", () => {
  const appearance = checkedReaderAppearance(null);
  assert.equal(readerAppearanceShortcut({ key: "2", ctrlKey: true }, appearance).theme, "sepia");
  assert.equal(readerAppearanceShortcut({ key: "3", metaKey: true }, appearance).theme, "dark");
  assert.equal(readerAppearanceShortcut({ key: "+", ctrlKey: true }, appearance).fontSize, 22);
  assert.equal(readerAppearanceShortcut({ key: "-", ctrlKey: true }, { ...appearance, fontSize: 14 }).fontSize, 14);
  assert.equal(readerAppearanceShortcut({ key: "=", metaKey: true }, { ...appearance, fontSize: 40 }).fontSize, 40);
  for (const event of [{ key: "2" }, { key: "2", ctrlKey: true, altKey: true }, { key: "2", ctrlKey: true, defaultPrevented: true }, { key: "2", ctrlKey: true, target: { closest: () => ({}) } }, { key: "c", ctrlKey: true }]) assert.equal(readerAppearanceShortcut(event, appearance), null);
});

test("paged reading turns complete viewports and reports chapter boundaries", () => {
  const root = { clientWidth: 800, scrollWidth: 3200, clientHeight: 600, scrollHeight: 600, scrollLeft: 0, scrollTop: 0, dataset: { readerView: "single" } };
  const doc = { documentElement: root, scrollingElement: root };
  assert.deepEqual(readerPageState(doc), { current: 1, total: 4 });
  assert.equal(turnReaderPage(doc, -1), false);
  assert.equal(turnReaderPage(doc, 1), true); assert.equal(root.scrollLeft, 800);
  assert.equal(scrollFraction(doc), 1 / 3);
  restoreScroll(doc, 1); assert.equal(root.scrollLeft, 2400);
  assert.equal(turnReaderPage(doc, 1), false);
  assert.equal(turnReaderPage(doc, -1), true); assert.equal(root.scrollLeft, 1600);
});

test("scroll reading uses vertical progress independently of horizontal page mode", () => {
  const root = { clientWidth: 800, scrollWidth: 800, clientHeight: 600, scrollHeight: 2400, scrollLeft: 0, scrollTop: 0, dataset: { readerView: "scroll" } };
  const doc = { documentElement: root, scrollingElement: root };
  assert.equal(turnReaderPage(doc, 1), true); assert.equal(root.scrollTop, 540);
  restoreScroll(doc, .5); assert.equal(root.scrollTop, 900); assert.equal(scrollFraction(doc), .5);
});

test("keyboard reading leaves form editing, text selection and browser shortcuts intact", () => {
  assert.equal(readerKeyboardDirection({ key: "ArrowRight", target: null }), 1);
  assert.equal(readerKeyboardDirection({ key: "PageUp", target: null }), -1);
  assert.equal(readerKeyboardDirection({ key: " ", shiftKey: true, target: null }), -1);
  assert.equal(readerKeyboardDirection({ key: "ArrowRight", shiftKey: true, target: null }), 0);
  assert.equal(readerKeyboardDirection({ key: "ArrowRight", ctrlKey: true, target: null }), 0);
  assert.equal(readerKeyboardDirection({ key: " ", target: { closest: () => ({}) } }), 0);
});

test("book search returns exact text offsets, handles Bengali and bounds repeated matches", () => {
  assert.deepEqual(chapterMatches("আগে বাংলা পরে বাংলা", "বাংলা", 3).map(({ start, end, chapter }) => ({ start, end, chapter })), [{ start: 4, end: 9, chapter: 3 }, { start: 14, end: 19, chapter: 3 }]);
  assert.equal(chapterMatches("A book and a BOOK", "book", 0).length, 2);
  assert.equal(chapterMatches("abc", "   ", 0).length, 0);
  assert.equal(chapterMatches("a".repeat(200), "a", 0).length, 100);
});
