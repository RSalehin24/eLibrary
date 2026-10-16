import assert from "node:assert/strict";
import test from "node:test";
import { installLabObservers } from "./browser_metrics.mjs";

function collector(t) {
  const callbacks = new Map();
  const previous = { window: globalThis.window, observer: globalThis.PerformanceObserver };
  t.after(() => { globalThis.window = previous.window; globalThis.PerformanceObserver = previous.observer; });
  globalThis.window = {};
  globalThis.PerformanceObserver = class {
    static supportedEntryTypes = ["largest-contentful-paint", "layout-shift", "event"];
    constructor(callback) { this.callback = callback; }
    observe({ type }) { callbacks.set(type, this.callback); }
  };
  installLabObservers();
  return { metrics: window.libraryLabMetrics, send: (type, entries) => callbacks.get(type)({ getEntries: () => entries }) };
}

test("layout measurements use the largest session and exclude recent input", (t) => {
  const { metrics, send } = collector(t);
  send("layout-shift", [
    { startTime: 100, value: 0.1 }, { startTime: 500, value: 0.05 },
    { startTime: 800, value: 1, hadRecentInput: true }, { startTime: 1500, value: 0.2 },
  ]);
  assert.equal(metrics.cls, 0.2);
});

test("continuous layout sessions stop at five seconds", (t) => {
  const { metrics, send } = collector(t);
  send("layout-shift", Array.from({ length: 7 }, (_, index) => ({ startTime: 100 + index * 900, value: 0.1 })));
  assert.ok(Math.abs(metrics.cls - 0.6) < 0.00001);
});

test("layout windows begin at the first shift rather than navigation start", (t) => {
  const { metrics, send } = collector(t);
  send("layout-shift", Array.from({ length: 6 }, (_, index) => ({ startTime: 950 + index * 900, value: 0.1 })));
  assert.ok(Math.abs(metrics.cls - 0.6) < 0.00001);
});

test("only real interaction durations and the latest contentful paint are retained", (t) => {
  const { metrics, send } = collector(t);
  send("event", [{ interactionId: 0, duration: 1000 }, { interactionId: 1, duration: 24 }, { interactionId: 2, duration: 16 }]);
  send("largest-contentful-paint", [{ startTime: 120 }, { startTime: 240 }]);
  assert.equal(metrics.max_interaction_duration_ms, 24);
  assert.equal(metrics.lcp_ms, 240);
  assert.ok(!JSON.stringify(metrics).includes("interactionId"));
});
