import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";
import { savedSchedule, finishPreviousDiscovery } from "./automation-fixture.mjs";

test("the account directory searches real accounts and exposes identity, security and management together", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/manage/users-access/"); await setLanguage(page, "en");
  const search = page.getByRole("search");
  await search.getByLabel("Name, email or permission", { exact: true }).fill(fixture.managed_reader.email);
  await search.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(url => url.searchParams.get("q") === fixture.managed_reader.email);
  const rows = page.locator(".account-directory tbody tr"); await expect(rows).toHaveCount(1);
  expect((await rows.locator(".admin-record-copy").textContent()).split(fixture.managed_reader.email).length - 1).toBe(1);
  await expect(rows).toContainText("Active"); await expect(rows).toContainText("Two-step verification off");
  await expect(rows.getByRole("link", { name: /^Open Account:/ })).toHaveAttribute("href", `/manage/users-access/${fixture.managed_reader.id}/`);
  await setLanguage(page, "bn");
  await expect(page.locator('input[name="q"]')).toHaveValue(fixture.managed_reader.email);
  await rows.getByRole("link", { name: /^অ্যাকাউন্ট খুলুন:/ }).click();
  await expect(page.getByLabel("পাঠকের নাম", { exact: true })).toBeVisible();
});

test("schedule filters retain exact counts, clear to the full list and do not queue work on browsing", async ({ page }) => {
  await useAccount(page, "source_processor"); const { automation } = await savedSchedule(page);
  let runs = 0; page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/runs/")) runs += 1; });
  await page.goto("/manage/automations/");
  await setLanguage(page, "en");
  const search = page.getByRole("search");
  await search.getByLabel("Search Schedules", { exact: true }).fill(automation.name);
  await search.getByLabel("Status", { exact: true }).selectOption("disabled");
  await expect(search.getByLabel("Frequency", { exact: true })).not.toBeVisible();
  await search.getByRole("button", { name: "Filters", exact: true }).click();
  await search.getByLabel("Frequency", { exact: true }).selectOption("daily");
  await search.getByLabel("Sort", { exact: true }).selectOption("next_run");
  await search.getByRole("button", { name: "Filters", exact: true }).click();
  await expect(search.getByLabel("Frequency", { exact: true })).not.toBeVisible();
  await search.getByRole("button", { name: "Filters", exact: true }).click();
  await expect(search.getByLabel("Frequency", { exact: true })).toHaveValue("daily");
  await expect(search.getByLabel("Sort", { exact: true })).toHaveValue("next_run");
  await search.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(url => url.searchParams.get("q") === automation.name && url.searchParams.get("enabled") === "disabled" && url.searchParams.get("frequency") === "daily" && url.searchParams.get("sort") === "next_run");
  const rows = page.locator(".automation-directory tbody tr"); await expect(rows).toHaveCount(1);
  await expect(page.locator(".admin-results-heading .count-badge")).toHaveText("1");
  await expect(rows).toContainText("Schedule paused");
  await expect(rows.getByRole("button", { name: "Run Now", exact: true })).toBeVisible();
  await expect(rows.getByRole("link", { name: "Settings & History", exact: true })).toHaveAttribute("href", `/manage/automations/${automation.id}/`);
  await page.getByRole("link", { name: "Clear all filters", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/automations\/$/); expect(runs).toBe(0);
  await page.goto(`/manage/automations/${automation.id}/`);
  await expect(page.getByText("Schedule paused", { exact: true })).toBeVisible();
});

test("a schedule runs directly from its row once while retaining the saved next run", async ({ page }) => {
  await useAccount(page, "source_processor"); const { automation, headers } = await savedSchedule(page);
  await finishPreviousDiscovery(page, headers);
  await page.goto(`/manage/automations/?q=${encodeURIComponent(automation.name)}`);
  const row = page.locator(".automation-directory tbody tr"); await expect(row).toHaveCount(1);
  const accepted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/automations/${automation.id}/runs/`));
  await row.getByRole("button", { name: "এখনই চালান", exact: true }).click();
  const response = await accepted; expect(response.status()).toBe(202); const result = await response.json();
  try {
    await expect(row.getByRole("status")).toContainText("কাজ যোগ হয়েছে");
    await expect(row.getByRole("button", { name: "এখনই চালান", exact: true })).toHaveCount(0);
    await expect(row.getByRole("link", { name: "কাজের অগ্রগতি দেখুন", exact: true })).toHaveAttribute("href", `/manage/jobs/${result.job_id}/`);
    const current = await (await page.request.get(`/api/v1/manage/automations/${automation.id}/`)).json();
    expect(current.next_run_at).toBe(automation.next_run_at); expect(current.updated_at).toBe(automation.updated_at); expect(current.enabled).toBe(false);
  } finally {
    const job = await (await page.request.get(`/api/v1/manage/jobs/${result.job_id}/`)).json();
    expect((await page.request.post(`/api/v1/manage/jobs/${result.job_id}/`, { headers, data: { action: "cancel", expected_updated_at: job.updated_at } })).status()).toBe(202);
  }
});
