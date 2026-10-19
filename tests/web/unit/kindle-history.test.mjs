import { test } from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { kindleHistoryQuery, kindleCanResend, kindleResendHref, kindleResendRecipients } = await typescriptModule(new URL("../../../app/web/src/lib/kindle-history.ts", import.meta.url));

test("Kindle filters preserve combinations and exclude unrelated query keys", () => {
  const query = new URLSearchParams(kindleHistoryQuery({ q: "বই", contributor: "লেখক", category: "cat", sort: "title", from_date: "2026-10-18", cursor: "stale", other: "ignored" }));
  assert.equal(query.get("q"), "বই");
  assert.equal(query.get("contributor"), "লেখক");
  assert.equal(query.get("from_date"), "2026-10-18");
  assert.equal(query.has("cursor"), false);
  assert.equal(query.has("other"), false);
});

test("resending is explicit and never chooses a newly added recipient by default", () => {
  const previous = { id: "request-id", book: { slug: "বাংলা-বই" }, recipients: [{ address: "old@kindle.com", outcome: "accepted" }, { address: "kept@kindle.com", outcome: "uncertain" }] };
  assert.deepEqual(kindleResendRecipients(previous, ["kept@kindle.com", "new@kindle.com"]), ["kept@kindle.com"]);
  assert.deepEqual(kindleResendRecipients(previous, ["new@kindle.com"]), []);
  const href = kindleResendHref(previous);
  assert.ok(href.endsWith("?resend=request-id"));
  assert.equal(href.includes("@"), false);
  for (const state of ["queued", "running", "retry_wait", "paused"]) assert.equal(kindleCanResend(state), false);
  for (const state of ["succeeded", "failed", "cancelled", "needs_attention"]) assert.equal(kindleCanResend(state), true);
});
