import assert from "node:assert/strict";
import { test } from "node:test";
import { ProgressWriter } from "../../../app/web/src/lib/progress-writer.ts";

const first = { last_location: "chapter:0:0.5", progress_percent: 25 };
const latest = { last_location: "chapter:0:0.55", progress_percent: 27.5 };

test("failed progress stays visible while new positions queue and explicit retry saves the latest", async () => {
  const writes = [];
  const statuses = [];
  const writer = new ProgressWriter(async (progress) => {
    writes.push(progress);
    if (writes.length === 1) throw new Error("Synthetic unavailable response");
  }, (status) => statuses.push(status));
  writer.enqueue(first);
  assert.equal(await writer.flush(), false);
  assert.equal(writer.hasFailed, true);
  const reported = statuses.length;
  writer.enqueue(latest);
  assert.equal(statuses.length, reported);
  assert.equal(statuses.at(-1), "failed");
  assert.equal(await writer.flush(), true);
  assert.deepEqual(writes, [first, latest]);
  assert.equal(writer.hasFailed, false);
  assert.equal(statuses.at(-1), "saved");
});

test("a failed in-flight write preserves newer queued progress and coalesces callers", async () => {
  let reject;
  const pending = new Promise((_resolve, fail) => { reject = fail; });
  const writes = [];
  const writer = new ProgressWriter((progress) => {
    writes.push(progress);
    return writes.length === 1 ? pending : Promise.resolve();
  }, () => {});
  writer.enqueue(first);
  const original = writer.flush();
  const concurrent = writer.flush();
  writer.enqueue(latest);
  reject(new Error("Synthetic transport failure"));
  assert.deepEqual(await Promise.all([original, concurrent]), [false, false]);
  assert.equal(await writer.flush(), true);
  assert.deepEqual(writes, [first, latest]);
});
