import { test, expect, useAccount } from "./fixtures.mjs";

async function openConsole(page) {
  await useAccount(page, "administrator");
  await page.route("**/api/v1/**", route => route.request().method() === "GET" ? route.continue() : route.abort());
  await page.goto("/manage/sources/");
  await page.getByRole("button", { name: "English", exact: true }).click();
}

async function currentJob(page) {
  const list = await (await page.request.get("/api/v1/manage/jobs/?page=1")).json();
  return (await page.request.get(`/api/v1/manage/jobs/${list.entries[0].id}/`)).json();
}

test("primary admin actions and navigation are visible with no link decoration", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await openConsole(page);
  for (const name of ["Fetch All", "Process All", "Schedule Automation"]) {
    const action = page.getByRole("button", { name, exact: true });
    await expect(action).toBeVisible(); const box = await action.boundingBox();
    expect(box.y + box.height).toBeLessThan(844); expect(box.height).toBeGreaterThanOrEqual(44);
  }
  await expect(page.locator(".admin-sidebar .workspace-nav a")).toHaveCount(9);
  const link = page.locator(".admin-sidebar a").first(); await link.hover();
  expect(await link.evaluate(element => getComputedStyle(element).textDecorationLine)).toBe("none");
  await expect(page.locator(".admin-topbar").getByRole("link", { name: "Sign In", exact: true })).toHaveCount(0);
  await expect(page.locator(".admin-topbar").getByRole("button", { name: "Sign Out", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  for (const name of ["সব বইয়ের তথ্য আনুন", "সব বই তৈরি করুন", "সময়সূচি তৈরি করুন"]) await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("Fetch All submits a full scan and shows progress without leaving the catalog", async ({ page }) => {
  await openConsole(page); const original = await currentJob(page); let command;
  await page.route("**/api/v1/manage/sources/discovery/", async route => {
    if (route.request().method() !== "POST") return route.continue();
    command = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: { operation_id: command.operation_id, status_url: `/api/v1/manage/jobs/${command.operation_id}/` } });
  });
  await page.route("**/api/v1/manage/jobs/*/", route => route.fulfill({ json: { ...original, id: command?.operation_id ?? original.id, state: "running", kind: "discover_source", discovered_pages: 3, discovered_entries: 180, actions: ["pause", "cancel"], error_code: "" } }));
  await page.getByRole("button", { name: "Fetch All", exact: true }).click();
  await expect.poll(() => command?.fetch_all).toBe(true);
  await expect(page.locator(".source-sync .source-operation")).toContainText("180");
  await expect(page.locator(".source-sync").getByRole("button", { name: "Pause", exact: true })).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/manage/sources/");
});

test("Process All queues a durable parent and offers inline pause resume and stop controls", async ({ page }) => {
  await openConsole(page); const original = await currentJob(page); let command;
  let job = { ...original, kind: "process_catalog", state: "running", bulk_total: 4164, bulk_queued: 50, bulk_rejected: 0, actions: ["pause", "cancel"], error_code: "" };
  await page.route("**/api/v1/manage/sources/process-all/", async route => {
    if (route.request().method() !== "POST") return route.continue();
    command = route.request().postDataJSON(); job.id = command.operation_id;
    await route.fulfill({ status: 202, json: { operation_id: command.operation_id, status_url: `/api/v1/manage/jobs/${command.operation_id}/` } });
  });
  await page.route("**/api/v1/manage/jobs/*/", async route => {
    if (route.request().method() === "POST") { const action = route.request().postDataJSON().action; job = { ...job, state: action === "pause" ? "paused" : action === "resume" ? "queued" : "cancelled", actions: action === "pause" ? ["resume", "cancel"] : action === "resume" ? ["pause", "cancel"] : [] }; return route.fulfill({ status: 202, json: { operation_id: job.id, status_url: `/api/v1/manage/jobs/${job.id}/` } }); }
    return route.fulfill({ json: job });
  });
  await page.getByRole("button", { name: "Process All", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Process All", exact: true }); await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Queue All Eligible Books", exact: true }).click();
  await expect(dialog).not.toBeVisible(); await expect.poll(() => command?.operation_id).toBeTruthy();
  const progress = page.locator(".process-all .source-operation"); await expect(progress).toContainText("50");
  for (const name of ["Pause Queueing", "Resume", "Stop Queueing"]) await progress.getByRole("button", { name, exact: true }).click();
  await expect(progress.locator(".status-label")).toHaveText("Cancelled");
  await expect(progress.getByRole("link", { name: "View Book Jobs", exact: true })).toHaveAttribute("href", `/manage/jobs/?parent_job=${command.operation_id}`);
});

test("automation can schedule full fetching and all eligible books directly from the catalog", async ({ page }) => {
  await openConsole(page); let command;
  const schedules = await (await page.request.get("/api/v1/manage/automations/?page=1")).json();
  let entries = schedules.entries;
  await page.route("**/api/v1/manage/automations/**", async route => {
    if (route.request().method() !== "POST") return route.fulfill({ json: { ...schedules, entries, pagination: { ...schedules.pagination, total_count: entries.length } } });
    command = route.request().postDataJSON(); const saved = { ...command, id: command.operation_id, next_run_at: "2027-01-01T20:00:00Z", updated_at: "2026-10-17T03:00:00Z", run_as_name: "Administrator" }; entries = [...entries, saved]; return route.fulfill({ status: 201, json: saved });
  });
  await page.getByRole("button", { name: "Schedule Automation", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Automation Schedule", exact: true });
  await dialog.getByLabel("Schedule Name", { exact: true }).fill("Daily catalog and book creation");
  await dialog.getByLabel("First Run Date", { exact: true }).fill("2027-01-02");
  const time = dialog.getByRole("group", { name: "Time", exact: true });
  await time.getByLabel("hours", { exact: true }).selectOption("2");
  await time.getByLabel("minutes", { exact: true }).selectOption("0");
  await time.getByLabel("AM or PM", { exact: true }).selectOption("AM");
  await dialog.getByLabel("Schedule Enabled", { exact: true }).check();
  await dialog.getByRole("button", { name: "Save Schedule", exact: true }).click();
  await expect.poll(() => command?.process_all).toBe(true); expect(command.fetch_all).toBe(true); expect(command.time_zone).toBe("Asia/Dhaka");
  expect(command.first_run_local).toBe("2027-01-02T02:00");
  await expect(dialog).not.toBeVisible(); await expect(page.locator(".source-scheduling").getByRole("status")).toContainText("Schedule saved");
});
