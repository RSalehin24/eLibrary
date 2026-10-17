import assert from "node:assert/strict";
import { test } from "node:test";
import { toggleSourcePage } from "../../../app/web/src/lib/source-selection.ts";

const source = (id, can_process = true) => ({ id, can_process });
const chosen = (entry) => ({ entry, operationId: `original-operation-${entry.id}` });

test("page selection skips unavailable sources and retains other pages and operation identities", () => {
  const existing = source("other-page"), first = source("first"), second = source("second");
  const current = { [existing.id]: chosen(existing), [first.id]: chosen(first) };
  const result = toggleSourcePage(current, [first, second, source("unavailable", false)]);
  assert.deepEqual(Object.keys(result), ["other-page", "first", "second"]);
  assert.equal(result.first, current.first); assert.equal(result["other-page"], current["other-page"]);
  assert.deepEqual(Object.keys(current), ["other-page", "first"]);
  assert.match(result.second.operationId, /^[0-9a-f-]{36}$/);
});

test("clearing a selected page preserves selections from other pages", () => {
  const first = source("first"), other = source("other");
  const current = { first: chosen(first), other: chosen(other) };
  assert.deepEqual(toggleSourcePage(current, [first, source("unavailable", false)]), { other: current.other });
});

test("selecting another page stops at the hundred-book limit without replacing earlier choices", () => {
  const current = Object.fromEntries(Array.from({ length: 99 }, (_, index) => { const entry = source(`existing-${index}`); return [entry.id, chosen(entry)]; }));
  const result = toggleSourcePage(current, [source("new-first"), source("new-second")]);
  assert.equal(Object.keys(result).length, 100); assert.ok(result["new-first"]); assert.equal(result["new-second"], undefined);
  assert.equal(result["existing-0"], current["existing-0"]); assert.equal(Object.keys(current).length, 99);
});
