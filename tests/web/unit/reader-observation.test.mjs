import assert from "node:assert/strict";
import { test } from "node:test";
import { observeReaderDocument } from "../../../app/web/src/lib/reader-observation.ts";

test("sandboxed reader observation uses the parent timer and stops when hidden or detached", () => {
  let sample;
  let cleared;
  const host = { document: { visibilityState: "visible" }, setInterval: (callback, delay) => {
    assert.equal(delay, 200); sample = callback; return 17;
  }, clearInterval: (identifier) => { cleared = identifier; } };
  globalThis.window = host;
  const chapter = { documentElement: { isConnected: true } };
  let captures = 0;
  try {
    const stop = observeReaderDocument(chapter, () => { captures += 1; });
    assert.equal(captures, 1);
    sample(); assert.equal(captures, 2);
    host.document.visibilityState = "hidden"; sample(); assert.equal(captures, 2);
    host.document.visibilityState = "visible"; chapter.documentElement.isConnected = false;
    sample(); assert.equal(captures, 2);
    stop(); assert.equal(cleared, 17);
  } finally { delete globalThis.window; }
});
