import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { savedQueueFilter, jobFilterQuery } = await typescriptModule(new URL("../../../app/web/src/lib/job-filters.ts", import.meta.url));
const { translateAdmin } = await typescriptModule(new URL("../../../app/web/src/lib/admin-language.ts", import.meta.url));

test("saved queue filters retain supported searches and diagnostic conditions", () => {
  const values = { view: "recovery", q: "বাংলা বই", kind: "process_source", coverage: "incomplete", layout: "multi_page", error_code: "source_content_incomplete", book: "ad397148-3433-4fa1-9cd3-76045a964a7f" };
  assert.deepEqual(savedQueueFilter(values), values);
  assert.deepEqual(Object.fromEntries(new URLSearchParams(jobFilterQuery(values))), values);
  assert.deepEqual(savedQueueFilter({ state: "", q: "" }), {});
});

test("unsafe and obsolete queue conditions cannot be applied", () => {
  for (const values of [{ state: "__proto__" }, { view: "constructor" }, { kind: "missing" }, { coverage: "full" }, { layout: "constructor" }, { layout: "multi_page/../../private" }, { error_code: "path/private" }, { q: "x".repeat(121) }, { book: "not-a-uuid" }, { page: "2" }, { input: "private" }, { q: ["invalid"] }]) assert.equal(savedQueueFilter(values), null);
});

test("queue query serialization omits pagination and empty filters", () => {
  assert.equal(jobFilterQuery({ page: "3", state: "", view: "active" }), "view=active");
});

test("queue views and verification states have English and Bengali labels", () => {
  assert.equal(translateAdmin("en", "পুনরুদ্ধারের কাজ"), "Recovery");
  assert.equal(translateAdmin("en", "লেখার যাচাই অসম্পূর্ণ"), "Source verification incomplete");
  assert.equal(translateAdmin("en", "এই বইয়ের সব কাজ"), "All Jobs for This Book");
  assert.equal(translateAdmin("en", "একাধিক পাতায় সূচিপত্র"), "Multi-page contents");
  assert.equal(translateAdmin("en", "সংগৃহীত সূচিপত্রের পাতা"), "Contents pages collected");
});
