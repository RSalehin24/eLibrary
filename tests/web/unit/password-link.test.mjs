import assert from "node:assert/strict";
import test from "node:test";
import { parsePasswordLink } from "../../../app/web/src/lib/password-link.ts";

test("password links accept fragments and retained email query links", () => {
  const ticket = { uid: "MQ", token: "synthetic-ticket" };
  assert.deepEqual(parsePasswordLink("https://library.test/create-password/#uid=MQ&token=synthetic-ticket"), ticket);
  assert.deepEqual(parsePasswordLink("https://library.test/reset-password/confirm/?uid=MQ&token=synthetic-ticket"), ticket);
});

test("ambiguous missing and oversized credentials are rejected", () => {
  for (const query of ["uid=MQ", "uid=MQ&token=", "uid=MQ&uid=Mg&token=value", "uid=MQ&token=one&token=two", `uid=MQ&token=${"x".repeat(257)}`]) assert.equal(parsePasswordLink(`https://library.test/#${query}`), null);
  assert.equal(parsePasswordLink("https://library.test/?uid=MQ&token=valid#token=partial"), null);
});
