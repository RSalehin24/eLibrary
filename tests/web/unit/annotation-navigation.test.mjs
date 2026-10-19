import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { annotationPosition } = await typescriptModule(new URL("../../../app/web/src/lib/annotation-position.ts", import.meta.url));
const { contentsTree, contentsIncludeChapter } = await typescriptModule(new URL("../../../app/web/src/lib/reader-contents.ts", import.meta.url));
const { submitNoteShortcut } = await typescriptModule(new URL("../../../app/web/src/lib/note-shortcut.ts", import.meta.url));
const session = { chapters: [{ path: "one.xhtml" }, { path: "two.xhtml" }] };

test("personal annotations restore exact bookmark, selection and structural legacy positions", () => {
  assert.deepEqual(annotationPosition({ location: "chapter:1:0.25" }, session), { chapter: 1, offset: .25 });
  const highlight = { chapter_href: "two.xhtml", selector: { start: 20, end: 30 }, text: "kept text", legacy_cfi: null };
  assert.deepEqual(annotationPosition(highlight, session), { chapter: 1, offset: 0, selection: highlight.selector, selectionText: "kept text", legacyCfi: undefined, legacyText: "kept text" });
  const legacy = annotationPosition({ ...highlight, selector: null, legacy_cfi: "epubcfi(/6/4!/4/2:0)" }, session);
  assert.equal(legacy.legacyCfi, "epubcfi(/6/4!/4/2:0)");
  assert.equal(annotationPosition({ ...highlight, chapter_href: "removed.xhtml" }, session).restoration, "missing");
  assert.equal(annotationPosition({ ...highlight, selector: null }, session).restoration, "missing");
});

test("nested contents retains heading-only parents and identifies current ancestors", () => {
  const navigation = [
    { label: "Part one", chapter_index: null, depth: 0, fragment: "" },
    { label: "One", chapter_index: 0, depth: 1, fragment: "" },
    { label: "Subheading", chapter_index: 0, depth: 2, fragment: "inside" },
    { label: "Part two", chapter_index: null, depth: 0, fragment: "" },
    { label: "Two", chapter_index: 1, depth: 1, fragment: "" },
  ];
  const tree = contentsTree(navigation);
  assert.equal(tree.length, 2);
  assert.equal(tree[0].children[0].children[0].label, "Subheading");
  assert.equal(contentsIncludeChapter(tree[0], 0), true);
  assert.equal(contentsIncludeChapter(tree[0], 1), false);
  assert.equal(contentsIncludeChapter(tree[1], 1), true);
  assert.deepEqual(contentsTree([]), []);
});

test("notes submit with Control or Command Enter while ordinary typing and repeats remain intact", () => {
  let saved = 0, prevented = 0;
  const form = { requestSubmit: () => saved++ }, event = { key: "Enter", preventDefault: () => prevented++ };
  for (const modifiers of [{ ctrlKey: true }, { metaKey: true }]) submitNoteShortcut({ ...event, ...modifiers }, form);
  assert.equal(saved, 2); assert.equal(prevented, 2);
  for (const modifiers of [{}, { ctrlKey: true, key: "a" }, { ctrlKey: true, repeat: true }, { metaKey: true, altKey: true }]) submitNoteShortcut({ ...event, ...modifiers }, form);
  assert.equal(saved, 2); assert.equal(prevented, 2);
});
