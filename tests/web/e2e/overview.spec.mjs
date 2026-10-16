import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("overview is private and shows each administrator's authorized sections", async ({ page }) => {
  await useAccount(page, "reader"); expect((await page.request.get("/manage/")).status()).toBe(404);
  expect((await page.request.get("/api/v1/manage/overview/")).status()).toBe(403);
  await useAccount(page, "editor"); await page.goto("/manage/");
  await expect(page.getByRole("heading", { name: "আপনার পরিচালনাযোগ্য বই", exact: true })).toBeVisible();
  for (const name of ["বইয়ের উৎস", "পাঠকের হিসাব", "প্রক্রিয়াকরণের কাজ", "আমন্ত্রণের কাজ"]) await expect(page.getByRole("heading", { name, exact: true })).toHaveCount(0);
  await useAccount(page, "source_processor"); await page.goto("/manage/");
  await expect(page.getByRole("heading", { name: "বইয়ের উৎস", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "প্রক্রিয়াকরণের কাজ", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "আমন্ত্রণের কাজ", exact: true })).toHaveCount(0);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
});

test("phone overview provides actionable processing and mail failures without crossing permissions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await useAccount(page, "administrator"); await page.goto("/manage/");
  const issue = page.locator(`a[href="/manage/jobs/${fixture.overview.processing_issue}/"]`);
  await expect(issue).toBeVisible(); await issue.click();
  await expect(page.locator(".status-label")).toHaveText("ব্যর্থ");
  await useAccount(page, "access_manager"); await page.goto("/manage/");
  await expect(page.getByRole("heading", { name: "আমন্ত্রণের কাজ", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "প্রক্রিয়াকরণের কাজ", exact: true })).toHaveCount(0);
  const mail = page.locator(`a[href="/manage/users-access/mail/${fixture.overview.mail_issue}/"]`); await expect(mail).toBeVisible();
  await page.screenshot({ path: "test-artifacts/foundation/overview-390.png", fullPage: true }); await mail.click();
  await expect(page.locator(".status-label")).toHaveText("পরীক্ষা করা প্রয়োজন");
  await expect(page.getByText("স্বয়ংক্রিয়ভাবে আবার পাঠানো হবে না", { exact: false })).toBeVisible();
});

test("overview polling refreshes work without repeating catalog summary reads", async ({ page }) => {
  await useAccount(page, "administrator"); const reads = { work: 0, summary: 0 };
  page.on("request", (request) => { const path = new URL(request.url()).pathname;
    if (path === "/api/v1/manage/overview/work/") reads.work += 1;
    if (path === "/api/v1/manage/overview/") reads.summary += 1;
  });
  await page.goto("/manage/"); await expect.poll(() => reads.work).toBeGreaterThan(0);
  expect(reads.summary).toBe(0);
  await page.getByRole("button", { name: "সব তথ্য আবার দেখুন", exact: true }).click();
  await expect.poll(() => reads.summary).toBe(1);
});

test("overview summary renders without JavaScript at 320 pixels", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, javaScriptEnabled: false, viewport: { width: 320, height: 800 } });
  const page = await context.newPage(); await useAccount(page, "editor");
  await page.goto("/manage/"); await expect(page.getByRole("heading", { name: "আপনার পরিচালনাযোগ্য বই", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "বই দেখুন →", exact: true })).toBeVisible(); await context.close();
});
