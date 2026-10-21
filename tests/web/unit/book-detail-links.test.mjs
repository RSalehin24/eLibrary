import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { bookDetailEntityPath } = await typescriptModule(new URL("../../../app/web/src/lib/book-detail-links.ts", import.meta.url));
const { translateSite } = await typescriptModule(new URL("../../../app/web/src/lib/site-language.ts", import.meta.url));
const { translateAdmin } = await typescriptModule(new URL("../../../app/web/src/lib/admin-language.ts", import.meta.url));
const { bookDetailContents } = await typescriptModule(new URL("../../../app/web/src/lib/book-detail-contents.ts", import.meta.url));

test("bounded contents retain nested sections and following sibling chapters", () => {
  assert.deepEqual(bookDetailContents([
    { label: "Part one", depth: 0 }, { label: "Chapter one", depth: 1 },
    { label: "Chapter two", depth: 1 }, { label: "Part two", depth: 0 },
  ]), [
    { label: "Part one", children: [{ label: "Chapter one", children: [] }, { label: "Chapter two", children: [] }] },
    { label: "Part two", children: [] },
  ]);
});

test("book credits link to the exact public contributor role", () => {
  assert.equal(bookDetailEntityPath({ kind: "contributors", slug: "translator-name", role: "translator" }), "/contributors/translator-name/?role=translator");
  assert.equal(bookDetailEntityPath({ kind: "categories", slug: "fiction" }), "/categories/fiction/");
});

test("personal detail links keep private books inside their own library", () => {
  for (const [kind, filter] of [["contributors", "contributor"], ["categories", "category"], ["series", "series"]]) {
    const href = new URL(bookDetailEntityPath({ kind, slug: "নিজের বই", personal: true }), "http://library.test");
    assert.equal(href.pathname, "/my-books/");
    assert.equal(href.searchParams.get(filter), "নিজের বই");
  }
  assert.equal(bookDetailEntityPath({ kind: "contributors", slug: "editor-name", role: "editor", personal: true }), "/my-books/?contributor=editor-name&contributor_role=editor");
  assert.equal(bookDetailEntityPath({ kind: "categories", slug: "private-category", personal: true, view: "granted" }), "/my-books/?category=private-category&view=granted");
  assert.equal(bookDetailEntityPath({ kind: "categories", slug: "owned-category", personal: true, view: "all" }), "/my-books/?category=owned-category");
});

test("detail preview labels and automatic publication guidance are bilingual", () => {
  for (const label of ["প্রথম প্রকাশ", "প্রকাশনার ঠিকানা", "প্রকাশনার তথ্য", "উৎসর্গ", "বইয়ের সূচি দেখা হচ্ছে…", "এখানে সংক্ষিপ্ত তথ্য দেখানো হয়েছে। পুরো সূচি ও লেখা দেখতে বই পড়ুন।"]) {
    assert.notEqual(translateSite("en", label), label);
    assert.equal(translateSite("bn", label), label);
  }
  const guidance = "ওয়েবসাইট থেকে নতুন করে লেখা এনে HTML ও EPUB তৈরি হবে। আগের ফাইল ও পাঠকের নোট সংরক্ষিত থাকবে। স্বয়ংক্রিয় যাচাই সফল হলে বই প্রকাশিত হবে।";
  assert.doesNotMatch(translateAdmin("bn", guidance), /পর্যালোচনা/);
  assert.match(translateAdmin("en", guidance), /automatically after successful verification/);
});
