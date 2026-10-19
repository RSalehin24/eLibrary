import { test } from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { toggleAccessScope, bulkGrantCount, bulkGrantEntries, dhakaDateTimeParts, dhakaDateTimeValue } = await typescriptModule(new URL("../../../app/web/src/lib/bulk-access.ts", import.meta.url));

test("bulk permission selection enforces mutually exclusive reading modes", () => {
  assert.deepEqual(toggleAccessScope(["read:durable", "send:kindle"], "read:once"), ["send:kindle", "read:once"]);
  assert.deepEqual(toggleAccessScope(["read:once", "download:file"], "read:durable"), ["download:file", "read:durable"]);
  assert.deepEqual(toggleAccessScope(["read:once"], "read:once"), []);
});

test("bulk commands cross scopes and targets with separate replay identifiers", () => {
  const selection = { kind: "book", scopes: ["read:durable", "download:file"], targets: [{ id: "first", name: "প্রথম" }, { id: "second", name: "দ্বিতীয়" }], expiresAt: null, notes: "পাঠক" };
  let identifier = 0;
  const entries = bulkGrantEntries(selection, () => `command-${++identifier}`);
  assert.equal(bulkGrantCount(selection), 4);
  assert.deepEqual(entries.map(({ id, scope, book }) => [id, scope, book]), [["command-1", "read:durable", "first"], ["command-2", "download:file", "first"], ["command-3", "read:durable", "second"], ["command-4", "download:file", "second"]]);
  assert.ok(entries.every((entry) => entry.notes === "পাঠক" && entry.expires_at === null && !("category" in entry)));
});

test("account-wide and writer/category permissions use their correct target fields", () => {
  const selection = { kind: "account", scopes: ["send:kindle"], targets: [{ id: "ignored", name: "" }], expiresAt: "2026-10-18T06:00:00.000Z", notes: "" };
  const [account] = bulkGrantEntries(selection, () => "id");
  assert.deepEqual(account, { id: "id", scope: "send:kindle", expires_at: selection.expiresAt, notes: "" });
  assert.equal(bulkGrantEntries({ ...selection, kind: "author" }, () => "id")[0].contributor, "ignored");
  assert.equal(bulkGrantEntries({ ...selection, kind: "category" }, () => "id")[0].category, "ignored");
  assert.equal(bulkGrantCount({ ...selection, targets: [] }), 1);
});

test("permission expiry uses Dhaka independently of the browser timezone", () => {
  assert.deepEqual(dhakaDateTimeParts("2026-10-17T20:30:00.000Z"), { date: "2026-10-18", time: "02:30" });
  assert.equal(dhakaDateTimeValue("2026-10-18", "14:35"), "2026-10-18T08:35:00.000Z");
  assert.equal(dhakaDateTimeValue("", "14:35"), null);
  assert.deepEqual(dhakaDateTimeParts(null), { date: "", time: "02:00" });
});
