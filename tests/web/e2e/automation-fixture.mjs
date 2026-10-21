import { randomUUID } from "node:crypto";
import { expect } from "./fixtures.mjs";

export async function savedSchedule(page) {
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": session.csrf_token };
  const response = await page.request.post("/api/v1/manage/automations/", { headers, data: {
    operation_id: randomUUID(), name: `Immediate schedule ${randomUUID().slice(0, 8)}`, enabled: false,
    frequency: "daily", first_run_local: new Date(Date.now() + 86400000).toISOString().slice(0, 16), time_zone: "Asia/Dhaka",
    source_max_pages: 3, processing_limit: 2, fetch_all: false, process_all: false, catalog_scope: "unfinished", rebuild_updated: true,
  } });
  expect(response.status()).toBe(201);
  return { automation: await response.json(), headers };
}

export async function finishPreviousDiscovery(page, headers) {
  const response = await page.request.get("/api/v1/manage/sources/discovery/");
  expect(response.status()).toBe(200);
  const identifier = (await response.json()).active_operation_id;
  if (!identifier) return;
  const path = `/api/v1/manage/jobs/${identifier}/`;
  const job = await (await page.request.get(path)).json();
  expect(job.kind).toBe("discover_source");
  expect((await page.request.post(path, { headers, data: { action: "cancel", expected_updated_at: job.updated_at } })).status()).toBe(202);
}
