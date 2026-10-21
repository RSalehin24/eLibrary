import { test, expect, useAccount, setLanguage } from "./fixtures.mjs";
import { savedSchedule, finishPreviousDiscovery } from "./automation-fixture.mjs";

test("Run Now uses a disabled saved schedule once and preserves its next run", async ({ page }) => {
  await useAccount(page, "source_processor");
  const { automation, headers } = await savedSchedule(page);
  await finishPreviousDiscovery(page, headers);
  await page.goto(`/manage/automations/${automation.id}/`);
  await setLanguage(page, "en");
  const controls = page.getByRole("region", { name: "Run saved schedule now", exact: true });
  const requests = [];
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith(`/automations/${automation.id}/runs/`)) requests.push(request.postDataJSON()); });
  const accepted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/automations/${automation.id}/runs/`));
  await controls.getByRole("button", { name: "Run Now", exact: true }).click();
  const response = await accepted;
  expect(response.status()).toBe(202);
  const result = await response.json();
  try {
    await expect(controls.getByRole("status")).toContainText("Run queued");
    expect(requests).toHaveLength(1);
    const replay = await page.request.post(`/api/v1/manage/automations/${automation.id}/runs/`, { headers, data: requests[0] });
    expect(await replay.json()).toEqual(result);
    const current = await (await page.request.get(`/api/v1/manage/automations/${automation.id}/`)).json();
    expect(current.next_run_at).toBe(automation.next_run_at);
    expect(current.updated_at).toBe(automation.updated_at);
    expect(current.enabled).toBe(false);
    await setLanguage(page, "bn");
    await expect(page.getByRole("region", { name: "সময়সূচি এখনই চালান", exact: true }).getByRole("status")).toContainText("কাজ যোগ হয়েছে");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally {
    if (result.job_id) {
      const job = await (await page.request.get(`/api/v1/manage/jobs/${result.job_id}/`)).json();
      expect((await page.request.post(`/api/v1/manage/jobs/${result.job_id}/`, { headers, data: { action: "cancel", expected_updated_at: job.updated_at } })).status()).toBe(202);
    }
  }
});

test("an uncertain manual run is not submitted twice", async ({ page }) => {
  await useAccount(page, "source_processor");
  const { automation } = await savedSchedule(page);
  await page.goto(`/manage/automations/${automation.id}/`);
  let writes = 0;
  await page.route(`**/api/v1/manage/automations/${automation.id}/runs/`, async route => {
    writes += 1;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", field_errors: {} }) });
  });
  const controls = page.getByRole("region", { name: "সময়সূচি এখনই চালান", exact: true });
  await controls.getByRole("button", { name: "এখনই চালান", exact: true }).click();
  await expect(controls.getByRole("button", { name: "এখনই চালান", exact: true })).toBeDisabled();
  await expect(controls.getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  expect(writes).toBe(1);
});
