import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { bookReadingLocation } = await typescriptModule(new URL("../../../app/web/src/lib/book-reading-location.ts", import.meta.url));
const { bookmarkTextLocation } = await typescriptModule(new URL("../../../app/web/src/lib/bookmark-text-position.ts", import.meta.url));
const chapters = [{ label: "প্রথম অধ্যায়", path: "a.xhtml" }, { label: "দ্বিতীয় অধ্যায়", path: "b.xhtml", idref: "second", spine_index: 1 }];

test("book summaries describe saved chapter positions using the actual prepared edition", () => {
  assert.deepEqual(bookReadingLocation({ last_location: "chapter:1:0.4", progress_percent: 70 }, chapters), { label: "দ্বিতীয় অধ্যায়", number: 2, total: 2, percent: 40 });
  assert.deepEqual(bookReadingLocation({ last_location: "b.xhtml#section", progress_percent: 70 }, chapters), { label: "দ্বিতীয় অধ্যায়", number: 2, total: 2, percent: null });
});

test("book summaries do not guess a chapter from progress or expose unresolved legacy positions", () => {
  for (const last_location of ["", "chapter:99:0.4", "chapter:-1:0", "chapter:1:9", "unknown.xhtml#section", "epubcfi(bad)"]) {
    assert.equal(bookReadingLocation({ last_location, progress_percent: 70 }, chapters), null);
  }
  assert.equal(bookReadingLocation({ last_location: "chapter:0:0", progress_percent: 0 }, []), null);
});

test("a proven legacy CFI identifies its chapter without inventing an exact chapter percentage", () => {
  assert.deepEqual(bookReadingLocation({ last_location: "epubcfi(/6/4[second]!/4/2/1:0)", progress_percent: 70 }, chapters), { label: "দ্বিতীয় অধ্যায়", number: 2, total: 2, percent: null });
});

test("book summaries label text-anchor chapters without exposing their serialized quotation", () => {
  const last_location = bookmarkTextLocation({ chapter: 1, offset: 123, quote: "বাংলা পাঠকের" });
  assert.deepEqual(bookReadingLocation({ last_location, progress_percent: 70 }, chapters), { label: "দ্বিতীয় অধ্যায়", number: 2, total: 2, percent: null });
});
