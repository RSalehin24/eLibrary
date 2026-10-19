import { test } from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";

const { generateInitialPassword } = await typescriptModule(new URL("../../../app/web/src/lib/initial-password.ts", import.meta.url));

test("initial passwords use exactly 24 browser cryptographic random bytes", () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  let calls = 0;
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: { getRandomValues: bytes => {
    calls += 1; assert.equal(bytes.length, 24); assert.ok(bytes instanceof Uint8Array);
    for (let index = 0; index < bytes.length; index += 1) bytes[index] = index;
    return bytes;
  } } });
  try { assert.equal(generateInitialPassword(), "aA!000102030405060708090a0b0c0d0e0f1011121314151617"); assert.equal(calls, 1); }
  finally { if (original) Object.defineProperty(globalThis, "crypto", original); else delete globalThis.crypto; }
});
