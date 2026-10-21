import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";

const { cfiMediaTarget, cfiRange } = await typescriptModule(new URL("../../../app/web/src/lib/reader-cfi.ts", import.meta.url));
const { restoreLegacyCfi } = await typescriptModule(new URL("../../../app/web/src/lib/reader-media-position.ts", import.meta.url));
const { fittedMediaBounds } = await typescriptModule(new URL("../../../app/web/src/lib/reader-media-geometry.ts", import.meta.url));
const { restoreAnchor } = await typescriptModule(new URL("../../../app/web/src/lib/reader-document.ts", import.meta.url));

function mediaDocument(kind = "audio") {
  const element = { nodeType: 1, localName: kind, id: "media", isConnected: true, readyState: 4, duration: 4, currentTime: 0, pauses: 0, pause() { this.pauses++; }, getBoundingClientRect: () => ({ left: 100 - root.scrollLeft, top: 1500 - root.scrollTop, width: 200, height: 600 }) };
  const body = { nodeType: 1, children: { item: index => index === 0 ? element : null }, contains: node => node === element };
  const root = { nodeType: 1, dataset: {}, children: { item: index => index === 1 ? body : null }, clientWidth: 1000, clientHeight: 900, scrollTop: 0, scrollLeft: 0 };
  const document = { documentElement: root, body, scrollingElement: root };
  element.ownerDocument = document;
  return { document, element, root };
}

test("media CFIs require the asserted element, its media kind and valid range endpoints", () => {
  const { document } = mediaDocument("img");
  assert.equal(cfiMediaTarget(document, "epubcfi(/6/2!/4/2[media]@50:80)").spatial.y, 80);
  assert.equal(cfiRange(document, "epubcfi(/6/2!/4/2@50:80)"), null);
  for (const value of ["/4/2[other]@50:80", "/4/2~1", "/4,/2@0:0,/4@100:100", "/4/2,~1,~0"]) {
    assert.equal(cfiMediaTarget(document, `epubcfi(/6/2!${value})`), null, value);
  }
  assert.equal(cfiMediaTarget(mediaDocument("audio").document, "epubcfi(/6/2!/4/2@50:80)"), null);
});

test("image coordinates restore the stored point within the image rather than only its top", () => {
  const { document, root } = mediaDocument("img");
  let failed = false;
  restoreLegacyCfi(document, "epubcfi(/6/2!/4/2@50:80)", { onFailure: () => { failed = true; } });
  assert.equal(root.scrollTop, 1680);
  assert.equal(failed, false);
});

test("image coordinates use rendered pixels inside letterboxing and honor authored object position", () => {
  const box = { left: 100, top: 1500, width: 200, height: 2000 };
  assert.deepEqual(fittedMediaBounds(box, { width: 1, height: 1 }, { fit: "contain", position: "50% 50%" }), { left: 100, top: 2400, width: 200, height: 200 });
  assert.deepEqual(fittedMediaBounds(box, { width: 1, height: 1 }, { fit: "contain", position: "left bottom" }), { left: 100, top: 3300, width: 200, height: 200 });
  assert.equal(fittedMediaBounds(box, { width: 1, height: 1 }, { fit: "contain", position: "calc(100% - 10px) 50%" }), null);
});

test("a restored image point stays at its viewport fraction when phone controls resize the frame", () => {
  const { document, root } = mediaDocument("img");
  let anchor;
  restoreLegacyCfi(document, "epubcfi(/6/2!/4/2@50:80)", { onFailure: assert.fail, onComplete: value => { anchor = value; } });
  assert.equal(anchor.viewportFraction, 1 / 3);
  root.clientHeight = 600;
  restoreAnchor(document, anchor, 0);
  assert.equal(root.scrollTop, 1780);
});

test("timed media restores seconds with visible controls and never starts playback", () => {
  const { document, element } = mediaDocument();
  let failures = 0;
  restoreLegacyCfi(document, "epubcfi(/6/2!/4/2~1.75)", { onFailure: () => failures++ });
  assert.equal(element.currentTime, 1.75);
  assert.equal(element.controls, true); assert.equal(element.autoplay, false);
  assert.equal(element.pauses, 1); assert.equal(failures, 0);
  restoreLegacyCfi(document, "epubcfi(/6/2!/4/2~8)", { onFailure: () => failures++ });
  assert.equal(failures, 1); assert.equal(element.currentTime, 1.75);
});

test("video CFIs restore both spatial and temporal coordinates without allowing reversed time ranges", () => {
  const { document, element, root } = mediaDocument("video");
  restoreLegacyCfi(document, "epubcfi(/6/2!/4/2~2.5@25:50)", { onFailure: assert.fail });
  assert.equal(element.currentTime, 2.5);
  assert.equal(root.scrollTop, 1500);
  assert.equal(cfiMediaTarget(document, "epubcfi(/6/2!/4/2,~3,~2)"), null);
});

test("waiting for media metadata is cancelled when the frame closes", () => {
  const { document, element } = mediaDocument();
  element.readyState = 0;
  const previous = globalThis.window;
  let timer, cleared, completed = false;
  globalThis.window = { setInterval: callback => { timer = callback; return 7; }, clearInterval: id => { cleared = id; } };
  try {
    const cancel = restoreLegacyCfi(document, "epubcfi(/6/2!/4/2~2)", { onFailure: assert.fail, onComplete: () => { completed = true; } });
    assert.equal(typeof timer, "function");
    assert.equal(completed, false);
    cancel(); assert.equal(cleared, 7); assert.equal(element.currentTime, 0);
  } finally { globalThis.window = previous; }
});

test("a rejected native media seek is reported instead of accepting a silent reset to zero", () => {
  const { document, element } = mediaDocument();
  element.readyState = 1;
  const previous = globalThis.window;
  let timer, failures = 0, completed = false;
  globalThis.window = { setInterval: callback => { timer = callback; return 8; }, clearInterval: () => {} };
  try {
    restoreLegacyCfi(document, "epubcfi(/6/2!/4/2~2)", { onFailure: () => failures++, onComplete: () => { completed = true; } });
    assert.equal(completed, false);
    element.readyState = 4; element.currentTime = 0; timer();
    assert.equal(failures, 1); assert.equal(completed, true);
  } finally { globalThis.window = previous; }
});
