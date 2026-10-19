import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("queue filters save and restore while bulk pause and resume keep job history", async ({ page }) => {
  await useAccount(page, "administrator");
  const identifier = fixture.preparation_job.id;
  await page.goto(`/manage/jobs/?q=${identifier}`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator(".job-card")).toHaveCount(1);
  const views = page.getByRole("navigation", { name: "Job views", exact: true });
  for (const name of ["Active Jobs", "History", "Recovery"]) await expect(views.getByRole("link", { name, exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: "Select available jobs on this page", exact: true }).check();
  const controls = page.getByRole("region", { name: "Selected job controls", exact: true });
  await controls.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(controls.getByRole("status")).toContainText("1");
  await expect(page.locator(".job-card")).toContainText("Paused");
  await page.getByRole("checkbox", { name: "Select available jobs on this page", exact: true }).check();
  await controls.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(page.locator(".job-card")).toContainText("Queued");
  const name = `Queue ${randomUUID()}`;
  let saved;
  try {
    await page.getByText("Save these filters", { exact: true }).click();
    await page.getByLabel("Filter name", { exact: true }).fill(name);
    const accepted = page.waitForResponse(response => response.url().includes("/me/saved-filters/") && response.request().method() === "POST");
    await page.locator(".saved-filter-create").getByRole("button", { name: "Save", exact: true }).click();
    const response = await accepted;
    expect(response.status()).toBe(201); saved = (await response.json()).id;
    await page.getByRole("link", { name: "Clear all filters", exact: true }).click();
    await page.locator(".saved-filter-list").getByRole("link", { name, exact: true }).click();
    await expect(page.getByRole("searchbox", { name: "Search jobs", exact: true })).toHaveValue(identifier);
    await expect(page.locator(".job-card")).toHaveCount(1);
    await page.getByRole("button", { name: `${name}: Delete saved filter`, exact: true }).click();
    await expect(page.locator(".saved-filter-list").getByRole("link", { name, exact: true })).toHaveCount(0); saved = undefined;
    const detail = await (await page.request.get(`/api/v1/manage/jobs/${identifier}/`)).json();
    expect(detail.state).toBe("queued");
    await page.getByRole("button", { name: "বাংলা", exact: true }).click();
    await expect(page.getByRole("searchbox", { name: "কাজ খুঁজুন", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  } finally {
    if (saved) {
      const session = await (await page.request.get("/api/v1/auth/session/")).json();
      await page.request.delete(`/api/v1/me/saved-filters/${saved}/`, { headers: { "X-CSRFToken": session.csrf_token } });
    }
  }
});

test("failed source selections expose revision-pinned retry recreate and reversible archive controls", async ({ page }) => {
  await useAccount(page, "administrator");
  const identifier = fixture.preparation_job.id;
  const detail = await (await page.request.get(`/api/v1/manage/jobs/${identifier}/`)).json();
  const source = { ...detail, kind: "process_source", state: "failed", actions: [], source_recovery_actions: ["retry_source", "recreate_source", "archive_book"], source_defect: null,
    book: { ...detail.book, updated_at: detail.book?.updated_at ?? "2026-10-18T12:00:00Z" } };
  let current = source;
  const calls = [];
  await page.route("**/api/v1/manage/jobs/?*", route => route.fulfill({ json: { entries: [current], pagination: { page: 1, limit: 50, total_count: 1 } } }));
  await page.route("**/api/v1/manage/jobs/bulk-control/", async route => {
    const command = route.request().postDataJSON(); calls.push(command);
    current = { ...source, state: command.action === "archive_book" ? "cancelled" : "queued", source_recovery_actions: [], actions: [] };
    await route.fulfill({ json: { operation_id: command.operation_id, entries: [{ id: identifier, outcome: "accepted", code: "" }] } });
  });
  for (const [action, label] of [["retry_source", "Retry Saved Work"], ["recreate_source", "Recreate from Website"], ["archive_book", "Archive Books"]]) {
    current = source;
    await page.goto(`/manage/jobs/?q=${identifier}`);
    await page.getByRole("button", { name: "English", exact: true }).click();
    await expect(page.locator(".job-card .status-label")).toHaveText("Failed");
    await page.getByRole("checkbox", { name: "Select available jobs on this page", exact: true }).check();
    const controls = page.getByRole("region", { name: "Selected job controls", exact: true });
    await expect(controls.getByRole("button", { name: "Resume", exact: true })).toBeDisabled();
    await controls.getByRole("button", { name: label, exact: true }).click();
    await expect(controls.getByRole("status")).toContainText("1");
    const command = calls.at(-1);
    expect(command.action).toBe(action);
    expect(command.entries).toEqual([{ id: identifier, expected_updated_at: source.updated_at, ...(action === "retry_source" ? {} : { expected_book_updated_at: source.book.updated_at }) }]);
    expect(command.operation_id).toMatch(/^[0-9a-f-]{36}$/);
  }
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(page.getByRole("button", { name: "বই আর্কাইভে রাখুন", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
