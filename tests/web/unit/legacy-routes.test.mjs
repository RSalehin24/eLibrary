import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { legacyRouteTarget } = await typescriptModule(new URL("../../../app/web/src/lib/legacy-routes.ts", import.meta.url));

test("legacy catalog links retain combined filters and default to their original digital type", () => {
  const destination = new URL(legacyRouteTarget("library", { q: "বাংলা", author: "লেখক", category: "বিভাগ", sort: "title", page: "2", next: "https://attacker.test" }), "https://library.test");
  assert.equal(destination.pathname, "/catalog/");
  assert.equal(destination.searchParams.get("contributor"), "লেখক");
  assert.equal(destination.searchParams.get("contributor_role"), "author");
  assert.equal(destination.searchParams.get("record_type"), "digital");
  assert.equal(destination.searchParams.get("q"), "বাংলা");
  assert.equal(destination.searchParams.get("page"), "2");
  assert.equal(destination.searchParams.has("next"), false);
});

test("legacy directories retain role and physical inventory retains its filters", () => {
  assert.equal(legacyRouteTarget("translators", { q: "Translator" }), "/contributors/?q=Translator&role=translator");
  const destination = new URL(legacyRouteTarget("manual-books", { publisher: "প্রকাশক", binding: "hard_cover" }), "https://library.test");
  assert.equal(destination.pathname, "/physical-books/");
  assert.equal(destination.searchParams.get("record_type"), "manual");
  assert.equal(destination.searchParams.get("binding"), "hard_cover");
});

test("legacy processing aliases target filtered current workspaces", () => {
  assert.equal(legacyRouteTarget("on-hold", {}), "/manage/jobs/?view=recovery");
  assert.equal(legacyRouteTarget("processing-failed-requests", {}), "/manage/jobs/?view=recovery");
  assert.equal(legacyRouteTarget("create", {}), "/manage/sources/?status=unlinked");
  assert.equal(legacyRouteTarget("processing-automation", {}), "/manage/automations/");
  assert.equal(legacyRouteTarget("processing-incomplete-check", {}), "/manage/unfinished/");
  for (const route of ["multipage-toc", "processing-multi-page-toc"]) {
    assert.equal(legacyRouteTarget(route, {}), "/manage/jobs/?kind=process_source&layout=multi_page");
  }
  assert.equal(legacyRouteTarget("access", { next: "//attacker.test" }), "/manage/users-access/");
});

test("legacy reader never accepts an external manifest or bypasses the book access workflow", () => {
  assert.equal(legacyRouteTarget("reader", { slug: "বাংলা-বই", manifest: "https://attacker.test/book" }), "/my-books/%E0%A6%AC%E0%A6%BE%E0%A6%82%E0%A6%B2%E0%A6%BE-%E0%A6%AC%E0%A6%87/");
  assert.equal(legacyRouteTarget("reader", { slug: "//attacker.test" }), "/my-books/");
  assert.equal(legacyRouteTarget("reader", { manifest: "https://attacker.test" }), "/my-books/");
  for (const slug of [".", "..", "invalid%2Fslug", "book?next=unsafe"]) {
    assert.equal(legacyRouteTarget("reader", { slug }), "/my-books/");
  }
});

test("malformed, repeated and unknown old-route input is rejected", () => {
  assert.equal(legacyRouteTarget("library", { sort: "password" }), null);
  assert.equal(legacyRouteTarget("library", { q: ["one", "two"] }), null);
  assert.equal(legacyRouteTarget("library", { q: "bad\nvalue" }), null);
  assert.equal(legacyRouteTarget("unknown", {}), null);
  for (const route of ["__proto__", "constructor", "toString"]) {
    assert.equal(legacyRouteTarget(route, {}), null);
  }
});
