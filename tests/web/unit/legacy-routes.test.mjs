import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { legacyRouteTarget } = await typescriptModule(new URL("../../../app/web/src/lib/legacy-routes.ts", import.meta.url));

test("removed development aliases do not recreate retired surfaces or filters", () => {
  for (const route of ["library", "manual-books", "writers", "translators", "on-hold", "create", "processing-automation", "access"]) {
    assert.equal(legacyRouteTarget(route, { record_type: "manual", binding: "hard_cover", next: "//attacker.test" }), null);
  }
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
