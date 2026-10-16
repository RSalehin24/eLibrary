import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("job workspace rejects readers and metadata-only editors", async ({ page }) => {
  await useAccount(page, "reader");
  expect((await page.request.get("/manage/jobs/")).status()).toBe(404);
  expect((await page.request.get(`/api/v1/manage/jobs/${fixture.preparation_job.id}/`)).status()).toBe(403);
  await useAccount(page, "editor"); await page.goto("/manage/books/");
  await expect(page.locator(".workspace-nav").getByRole("link", { name: "কাজ", exact: true })).toHaveCount(0);
  expect((await page.request.get("/manage/jobs/")).status()).toBe(404);
});

test("invalid and missing job pages return 404", async ({ page }) => {
  await useAccount(page, "administrator");
  for (const query of ["page=0", "page=0x10", "page=1e2", "page=9999999", "page=1&page=2", "state=__proto__", "state=missing"]) expect((await page.request.get(`/manage/jobs/?${query}`)).status()).toBe(404);
  expect((await page.request.get("/manage/jobs/00000000-0000-0000-0000-000000000000/")).status()).toBe(404);
  expect((await page.request.get("/catalog/?page=0x10")).status()).toBe(404);
});

test("phone job details support pause resume and cancellation with confirmed states", async ({ page }) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/manage/jobs/${fixture.preparation_job.id}/`);
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  for (const [action, state] of [["স্থগিত করুন", "স্থগিত"], ["আবার চালু করুন", "অপেক্ষমাণ"], ["বাতিল করুন", "বাতিল"]]) {
    const button = page.getByRole("button", { name: action, exact: true });
    expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(44);
    await button.click(); await expect(page.locator(".status-label")).toHaveText(state);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/job-detail-390.png", fullPage: true });
  await page.goto("/manage/jobs/?state=cancelled");
  await expect(page.getByRole("heading", { name: fixture.reading_book.title, exact: true })).toBeVisible();
});

test("asset preparation returns a trackable command and conflicts are not replayed", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  await page.getByRole("button", { name: "পড়ার জন্য প্রস্তুত করুন", exact: true }).click();
  const link = page.getByRole("link", { name: "প্রস্তুতির কাজ দেখুন →", exact: true });
  await expect(link).toBeVisible(); await link.click();
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  const controls = [];
  await page.route("**/api/v1/manage/jobs/*/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    controls.push(route.request());
    await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "state_conflict", detail: "Synthetic revision conflict", field_errors: {} }) });
  });
  await page.getByRole("button", { name: "স্থগিত করুন", exact: true }).click();
  await expect(page.locator(".job-detail").getByRole("alert")).toContainText("কাজের অবস্থাটি বদলেছে");
  await expect(page.getByRole("button", { name: "স্থগিত করুন", exact: true })).toBeDisabled();
  expect(controls).toHaveLength(1);
});

test("job polling suspends when hidden and does not overlap slow reads", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/manage/jobs/");
  let releaseRead; const pending = new Promise((resolve) => { releaseRead = resolve; });
  const reads = [];
  await page.route("**/api/v1/manage/jobs/?*", async (route) => { reads.push(route.request()); await pending; await route.continue(); });
  await expect.poll(() => reads.length).toBe(1);
  await page.waitForTimeout(2_100);
  expect(reads).toHaveLength(1);
  releaseRead();
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" }); window.dispatchEvent(new Event("visibilitychange")); });
  const stoppedCount = reads.length;
  await page.waitForTimeout(2_100);
  expect(reads).toHaveLength(stoppedCount);
});
