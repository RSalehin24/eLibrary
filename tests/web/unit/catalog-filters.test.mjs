import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { savedCatalogFilter } = await typescriptModule(new URL("../../../app/web/src/lib/saved-catalog-filter.ts", import.meta.url));
const { catalogNeedsAccount, catalogFilterQuery, catalogHasConditions } = await typescriptModule(new URL("../../../app/web/src/lib/catalog-filters.ts", import.meta.url));
const { catalogFilterMessages } = await typescriptModule(new URL("../../../app/web/src/lib/catalog-filter-messages.ts", import.meta.url));

test("filter controls include English labels for every main action", () => {
  for (const label of ["সংরক্ষণ করুন", "এই ফিল্টার সংরক্ষণ করুন", "ফিল্টার মুছুন", "ফিল্টার", "প্রয়োগ করুন", "সংগ্রহ", "সব ফিল্টার মুছুন"]) assert.ok(catalogFilterMessages[label]);
});

test("previous saved author filters retain author scope without mutating persisted data", () => {
  const original = { author: "রবীন্দ্রনাথ ঠাকুর", category: "কবিতা", sort: "title" };
  assert.deepEqual(savedCatalogFilter(original), { contributor: "রবীন্দ্রনাথ ঠাকুর", contributor_role: "author", category: "কবিতা", sort: "title" });
  assert.equal(original.author, "রবীন্দ্রনাথ ঠাকুর");
  assert.equal(savedCatalogFilter({ author: "one", contributor: "two" }), null);
});

test("saved filters reject unsupported fields, values and unsafe sort expressions", () => {
  for (const parameters of [{ state: "published" }, { sort: "title;drop table" }, { ownership: "someone-else" }, { contributor_role: "invented" }, { q: "q".repeat(121) }, { category: "c".repeat(256) }, { category: ["poems"] }]) {
    assert.equal(savedCatalogFilter(parameters), null);
  }
  assert.deepEqual(savedCatalogFilter({ record_type: "manual", ownership: "mine", contributor_role: "translator" }), { ownership: "mine", contributor_role: "translator" });
});

test("ownership and personal collection dates require account scoped requests and caches", () => {
  assert.equal(catalogNeedsAccount({ ownership: "mine" }), true);
  assert.equal(catalogNeedsAccount({ sort: "requested_at" }), true);
  assert.equal(catalogNeedsAccount({ sort: "-requested_at" }), true);
  assert.equal(catalogNeedsAccount({ sort: "-created_at", ownership: "" }), false);
});

test("catalog links encode all selected filters and preserve Bengali names", () => {
  const encoded = catalogFilterQuery({ contributor: "বিভূতিভূষণ", category: "কথা & কাহিনি", q: "", sort: "-title", view: "owned" });
  assert.deepEqual(Object.fromEntries(new URLSearchParams(encoded)), { contributor: "বিভূতিভূষণ", category: "কথা & কাহিনি", sort: "-title", view: "owned" });
});

test("an empty server filter permits clearing an unsubmitted draft without changing its view", () => {
  assert.equal(catalogHasConditions({ record_type: "all", q: "", sort: "" }), false);
  assert.equal(catalogHasConditions({ record_type: "manual" }, "manual"), false);
  assert.equal(catalogHasConditions({ record_type: "manual" }), false);
});

test("submitted bibliographic filters keep their URL navigation and cached form state", () => {
  for (const condition of [{ q: "বই" }, { sort: "title" }, { contributor: "লেখক" }, { series: "সিরিজ" }]) {
    assert.equal(catalogHasConditions(condition, "manual"), true);
  }
});
