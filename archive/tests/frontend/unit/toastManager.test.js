import assert from "node:assert/strict";
import test from "node:test";

import { createToastManager } from "../../../app/frontend/src/utils/toastManager.js";

function createFakeScheduler() {
  let nextId = 1;
  let now = 0;
  const timers = new Map();

  return {
    clear(id) {
      timers.delete(id);
    },
    pendingCount() {
      return timers.size;
    },
    schedule(callback, delay) {
      const id = nextId;
      nextId += 1;
      timers.set(id, {
        callback,
        at: now + delay,
      });
      return id;
    },
    advance(milliseconds) {
      now += milliseconds;
      let ranTimer = true;
      while (ranTimer) {
        ranTimer = false;
        for (const [id, timer] of [...timers.entries()].sort(
          (left, right) => left[1].at - right[1].at,
        )) {
          if (timer.at > now) {
            continue;
          }
          timers.delete(id);
          timer.callback();
          ranTimer = true;
        }
      }
    },
  };
}

test("grouped notifications stay open for a quiet window and reset on new arrivals", () => {
  const scheduler = createFakeScheduler();
  const playedSounds = [];
  const manager = createToastManager({
    schedule: scheduler.schedule,
    clear: scheduler.clear,
    createId: (() => {
      let nextId = 1;
      return () => `toast-${nextId++}`;
    })(),
    playSound: (type) => playedSounds.push(type),
  });

  let snapshot = manager.getState();
  const unsubscribe = manager.subscribe((nextSnapshot) => {
    snapshot = nextSnapshot;
  });

  manager.push(
    {
      title: "Request failed",
      description: "First failure.",
      groupKey: "processing-failed",
      holdOpenMs: 120000,
    },
    "error",
  );

  assert.equal(snapshot.toasts.length, 1);
  assert.equal(snapshot.toasts[0].title, "Request failed");
  assert.deepEqual(playedSounds, ["error"]);
  assert.equal(scheduler.pendingCount(), 1);

  scheduler.advance(119000);
  assert.equal(snapshot.toasts.length, 1);

  manager.push(
    {
      title: "Requests failed",
      description: "Second failure.",
      groupKey: "processing-failed",
      holdOpenMs: 120000,
    },
    "error",
  );

  assert.equal(snapshot.toasts.length, 1);
  assert.equal(snapshot.toasts[0].title, "Requests failed");
  assert.equal(snapshot.toasts[0].description, "Second failure.");
  assert.deepEqual(playedSounds, ["error"]);
  assert.equal(scheduler.pendingCount(), 1);

  scheduler.advance(119000);
  assert.equal(snapshot.toasts.length, 1);

  scheduler.advance(1001);
  assert.equal(snapshot.toasts.length, 0);
  unsubscribe();
  manager.destroy();
});

test("muting keeps notifications visible while suppressing sound playback", () => {
  const scheduler = createFakeScheduler();
  const playedSounds = [];
  const manager = createToastManager({
    schedule: scheduler.schedule,
    clear: scheduler.clear,
    playSound: (type) => playedSounds.push(type),
  });

  let snapshot = manager.getState();
  const unsubscribe = manager.subscribe((nextSnapshot) => {
    snapshot = nextSnapshot;
  });

  manager.setMuted(true);
  manager.push("A muted success toast.", "success");

  assert.equal(snapshot.muted, true);
  assert.equal(snapshot.toasts.length, 1);
  assert.deepEqual(playedSounds, []);

  unsubscribe();
  manager.destroy();
});

test("sound type can differ from the visual toast type", () => {
  const scheduler = createFakeScheduler();
  const playedSounds = [];
  const manager = createToastManager({
    schedule: scheduler.schedule,
    clear: scheduler.clear,
    playSound: (type) => playedSounds.push(type),
  });

  manager.push(
    {
      title: "Duplicate detected",
      description: "Needs review.",
      type: "info",
      soundType: "error",
    },
    "info",
  );

  assert.deepEqual(playedSounds, ["error"]);
  manager.destroy();
});
