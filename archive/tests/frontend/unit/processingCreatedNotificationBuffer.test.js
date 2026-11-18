import assert from "node:assert/strict";
import test from "node:test";

import {
  createCreatedNotificationBuffer,
  createdNotificationDescription,
} from "../../../app/frontend/src/utils/processingCreatedNotificationBuffer.js";

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

test("created notifications are batched for three minutes", () => {
  const scheduler = createFakeScheduler();
  const flushedCounts = [];
  const buffer = createCreatedNotificationBuffer({
    intervalMs: 180000,
    onFlush: (count) => flushedCounts.push(count),
    schedule: scheduler.schedule,
    clear: scheduler.clear,
  });

  buffer.addCompletedCount(3);
  buffer.addCompletedCount(2);

  assert.equal(buffer.getPendingCount(), 5);
  assert.equal(flushedCounts.length, 0);
  assert.equal(scheduler.pendingCount(), 1);

  scheduler.advance(179999);
  assert.equal(flushedCounts.length, 0);

  scheduler.advance(1);
  assert.deepEqual(flushedCounts, [5]);
  assert.equal(buffer.getPendingCount(), 0);

  buffer.destroy();
});

test("created notifications can flush immediately when pipeline is done", () => {
  const scheduler = createFakeScheduler();
  const flushedCounts = [];
  const buffer = createCreatedNotificationBuffer({
    intervalMs: 180000,
    onFlush: (count) => flushedCounts.push(count),
    schedule: scheduler.schedule,
    clear: scheduler.clear,
  });

  buffer.addCompletedCount(10);
  const flushedNow = buffer.flushIfPending();

  assert.equal(flushedNow, 10);
  assert.deepEqual(flushedCounts, [10]);
  assert.equal(buffer.getPendingCount(), 0);
  assert.equal(scheduler.pendingCount(), 0);

  buffer.destroy();
});

test("created notification message stays consistent", () => {
  assert.equal(
    createdNotificationDescription(10),
    "10 books created.",
  );
});
