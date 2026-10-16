import assert from "node:assert/strict";
import { test } from "node:test";
import { UpdateCoordinator } from "../../../app/web/src/lib/update-coordinator.ts";

test("updates wait for progress saves and reject failed saves", async () => {
  const coordinator = new UpdateCoordinator();
  let release;
  const save = new Promise((resolve) => { release = resolve; });
  coordinator.register({ dirty: false, prepare: () => save });
  const pending = coordinator.prepare();
  release(false);
  assert.equal(await pending, false);
});

test("edits made while progress is saving still prevent reload", async () => {
  const coordinator = new UpdateCoordinator();
  let release;
  const save = new Promise((resolve) => { release = resolve; });
  coordinator.register({ dirty: false, prepare: () => save });
  const pending = coordinator.prepare();
  const remove = coordinator.register({ dirty: true });
  release(true);
  assert.equal(await pending, false);
  remove();
  assert.equal(await coordinator.prepare(), true);
});

test("unsaved edits block activation until they are saved or their editor closes", async () => {
  const coordinator = new UpdateCoordinator();
  const unregister = coordinator.register({ dirty: true });
  assert.equal(await coordinator.prepare(), false);
  unregister();
  assert.equal(await coordinator.prepare(), true);
});
