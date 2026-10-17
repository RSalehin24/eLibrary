import assert from "node:assert/strict";
import { test } from "node:test";
import { typescriptModule } from "./typescript-module.mjs";
const { bindReaderGestures } = await typescriptModule(new URL("../../../app/web/src/lib/reader-gestures.ts", import.meta.url));

function reader() {
  const listeners = new Map(), gestures = [], turns = [];
  let selected = false;
  const document = { getSelection: () => ({ isCollapsed: !selected }), addEventListener: (name, listener) => listeners.set(name, listener), removeEventListener: name => listeners.delete(name) };
  const stop = bindReaderGestures(document, { turn: value => turns.push(value), onGesture: value => gestures.push(value) });
  const send = (name, values) => listeners.get(name)?.({ target: null, cancelable: true, preventDefault() {}, ...values });
  return { gestures, turns, send, stop, listeners, select: value => { selected = value; } };
}
const touch = (x, y = 0) => ({ clientX: x, clientY: y });
function tap(reader, time, target = null) {
  reader.send("touchstart", { timeStamp: time, touches: [touch(10)], target });
  reader.send("touchend", { timeStamp: time + 20, touches: [], changedTouches: [touch(10)], target });
}

test("a nearby double tap toggles immersive reading once and ignores its synthetic mouse event", () => {
  const view = reader(); tap(view, 1000); tap(view, 1200);
  view.send("dblclick", { timeStamp: 1250 });
  assert.deepEqual(view.gestures, [{ kind: "immersive" }]);
  view.stop(); assert.equal(view.listeners.size, 0);
});

test("selection, links, cancellations and separated taps preserve ordinary document interaction", () => {
  const view = reader(); view.select(true); tap(view, 1000); tap(view, 1100);
  view.select(false); const link = { closest: () => ({}) };
  tap(view, 2000, link); tap(view, 2100, link);
  tap(view, 3000); view.send("touchcancel", {}); tap(view, 3100);
  tap(view, 4000); tap(view, 4400);
  assert.deepEqual(view.gestures, []);
});

test("horizontal swipes navigate while slow drags and vertical scrolling do not", () => {
  const view = reader();
  for (const [time, end, duration] of [[1000, touch(-120), 200], [2000, touch(120), 200], [3000, touch(120), 700], [4000, touch(120, 180), 200]]) {
    view.send("touchstart", { timeStamp: time, touches: [touch(0)] });
    view.send("touchend", { timeStamp: time + duration, touches: [], changedTouches: [end] });
  }
  assert.deepEqual(view.turns, [1, -1]); assert.deepEqual(view.gestures, []);
});

test("pinching resizes text and a stationary two-finger tap cycles the theme", () => {
  const view = reader();
  view.send("touchstart", { timeStamp: 1000, touches: [touch(0), touch(100)] });
  view.send("touchmove", { timeStamp: 1050, touches: [touch(-30), touch(130)] });
  view.send("touchend", { timeStamp: 1100, touches: [], changedTouches: [touch(-30), touch(130)] });
  view.send("touchstart", { timeStamp: 2000, touches: [touch(0), touch(100)] });
  view.send("touchend", { timeStamp: 2100, touches: [], changedTouches: [touch(0), touch(100)] });
  assert.deepEqual(view.gestures, [{ kind: "text", steps: 2 }, { kind: "theme" }]);
});
