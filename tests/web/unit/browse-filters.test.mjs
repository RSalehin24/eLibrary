import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { currentBrowseFilters, retiredFilterRedirect } = await typescriptModule(new URL("../../../app/web/src/lib/browse-filters.ts", import.meta.url));
const { managementNavigation, managementHome } = await typescriptModule(new URL("../../../app/web/src/lib/management-navigation.ts", import.meta.url));

test("retired browse controls cannot silently constrain old URLs or saved filters", () => {
  const original = { q: "বাংলা", category: "কবিতা", record_type: "manual", created_after: "2026-01-01", from_date: "2026-02-01" };
  assert.deepEqual(currentBrowseFilters(original), { q: "বাংলা", category: "কবিতা" });
  assert.equal(original.record_type, "manual");
  const destination = retiredFilterRedirect("/catalog/", { ...original, page: "9", sort: "title", view: "saved" });
  assert.deepEqual(Object.fromEntries(new URL(destination, "https://library.test").searchParams), { q: "বাংলা", category: "কবিতা", sort: "title", view: "saved" });
});

test("current URLs retain pagination and repeated unrelated parameters are preserved on cleanup", () => {
  assert.equal(retiredFilterRedirect("/my-books/", { q: "book", page: "2" }), null);
  assert.equal(retiredFilterRedirect("/kindle/", { to_date: "bad", page: "2" }), "/kindle/");
  assert.equal(retiredFilterRedirect("/catalog/", { record_type: "all", q: ["one", "two"] }), "/catalog/?q=one&q=two");
});

test("management navigation has six sections and chooses the first authorized destination", () => {
  const sections = ["overview", "sources", "books", "jobs", "automations", "users-access"];
  assert.equal(managementNavigation(sections).length, 6);
  assert.equal(managementHome(sections), "/manage/sources/");
  assert.equal(managementHome(["books"]), "/manage/books/");
  assert.equal(managementHome(["jobs"]), "/manage/jobs/");
  assert.equal(managementHome(["overview"]), "/manage/overview/");
  assert.deepEqual(managementNavigation(["sources"]).map(entry => entry.href), ["/manage/sources/"]);
});
