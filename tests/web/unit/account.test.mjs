import assert from "node:assert/strict";
import { test } from "node:test";
import { authenticatorCode } from "../totp.mjs";
import { returnPath } from "../../../app/web/src/lib/return-path.ts";

test("browser authenticator helper matches the RFC 6238 SHA-1 vector", () => {
  assert.equal(authenticatorCode("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 59_000), "287082");
  assert.throws(() => authenticatorCode("INVALID!"), /Invalid/);
});

test("authentication return paths keep internal deep links and reject external URLs", () => {
  assert.equal(returnPath("/reader/123/?chapter=2"), "/reader/123/?chapter=2");
  for (const path of ["//outside.test/", "https://outside.test/", "/\\outside.test/", "/\n/outside.test/"]) assert.equal(returnPath(path), "/my-books/");
});
