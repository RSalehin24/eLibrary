import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { validDirectoryDate, validDirectoryFilters, directorySortLabels } = await typescriptModule(new URL("../../../app/web/src/lib/entity-directory-filters.ts", import.meta.url));
const { legacyRouteTarget } = await typescriptModule(new URL("../../../app/web/src/lib/legacy-routes.ts", import.meta.url));
const { translateSite } = await typescriptModule(new URL("../../../app/web/src/lib/site-language.ts", import.meta.url));

test("directory dates validate calendar days and ordered inclusive ranges", () => {
  for (const value of ["2026-01-02", "2024-02-29"]) assert.equal(validDirectoryDate(value), true);
  for (const value of ["2026-02-30", "2025-02-29", "2026-01-01T00:00:00Z", "0000-01-01", "01/02/2026"]) assert.equal(validDirectoryDate(value), false);
  assert.equal(validDirectoryFilters({ created_after: "2026-01-02", created_before: "2026-01-02" }), true);
  assert.equal(validDirectoryFilters({ created_after: "2026-01-03", created_before: "2026-01-02" }), false);
  assert.equal(validDirectoryFilters({ sort: "constructor" }), false);
});

test("retired directory aliases cannot restore old type or date conditions", () => {
  for (const route of ["writers", "translators", "editors", "publishers"]) {
    assert.equal(legacyRouteTarget(route, { record_type: "manual", created_after: "2026-01-02" }), null);
  }
});

test("directory control labels are translated while source names remain authored", () => {
  for (const label of [...Object.values(directorySortLabels), "তালিকায় যোগের প্রথম তারিখ", "তালিকায় যোগের শেষ তারিখ", "তারিখগুলো ঢাকার সময় অনুযায়ী।"]) {
    assert.notEqual(translateSite("en", label), label);
  }
  assert.equal(translateSite("en", "বিভূতিভূষণ বন্দ্যোপাধ্যায়"), "বিভূতিভূষণ বন্দ্যোপাধ্যায়");
});
