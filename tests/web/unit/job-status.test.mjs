import assert from "node:assert/strict";
import { test } from "node:test";
import { isJobAction, jobPollingInterval } from "../../../app/web/src/lib/job-status.ts";

test("job refresh rates follow actual activity and back off after read failures", () => {
  assert.equal(jobPollingInterval([], 0), 15_000);
  assert.equal(jobPollingInterval([{ state: "succeeded" }], 0), 15_000);
  for (const state of ["running", "queued", "retry_wait"]) assert.equal(jobPollingInterval([{ state }], 0), 2_000);
  assert.equal(jobPollingInterval([{ state: "running" }], 1), 10_000);
  assert.equal(jobPollingInterval([{ state: "running" }], 20), 60_000);
});

test("job actions accept only the supported control commands", () => {
  for (const action of ["pause", "resume", "cancel"]) assert.equal(isJobAction(action), true);
  for (const action of ["retry", "delete", "", "__proto__"]) assert.equal(isJobAction(action), false);
});
