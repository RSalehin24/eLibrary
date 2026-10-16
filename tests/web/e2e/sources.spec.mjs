import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("sources reject readers and metadata-only editors", async ({ page }) => {
  for (const account of ["reader", "editor", "access_manager"]) {
    await useAccount(page, account);
    expect((await page.request.get("/manage/sources/")).status()).toBe(404);
    expect((await page.request.get("/api/v1/manage/sources/")).status()).toBe(403);
  }
});

test("source search and pagination use private server-rendered pages", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.goto(`/manage/sources/?q=${fixture.sources.query}`);
  await expect(page.getByRole("heading", { name: "বইয়ের উৎস", exact: true })).toBeVisible();
  await expect(page.locator(".job-card")).toHaveCount(50);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await page.getByRole("link", { name: "পরের পাতা", exact: true }).click(); await expect(page.locator(".job-card")).toHaveCount(1);
  await page.goto(`/manage/sources/?q=${fixture.sources.query}&status=linked`); await expect(page.locator(".job-card")).toHaveCount(1);
  await expect(page.locator(".job-card")).toContainText(fixture.reading_book.title);
  expect(await page.locator("body").textContent()).not.toContain("private-source-fixture");
  for (const query of ["page=0", "page=1e2", "status=__proto__", "page=999999999"]) expect((await page.request.get(`/manage/sources/?${query}`)).status()).toBe(404);
});

test("processors inspect a linked source and request asset preparation without metadata access", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/manage/sources/${fixture.sources.linked.id}/`);
  await expect(page.getByRole("heading", { name: fixture.sources.linked.title, exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "বইয়ের তথ্য পর্যালোচনা করুন →", exact: true })).toHaveCount(0);
  const external = page.getByRole("link", { name: "মূল উৎস খুলুন (নতুন ট্যাব) ↗", exact: true });
  await expect(external).toHaveAttribute("target", "_blank"); await expect(external).toHaveAttribute("rel", "noopener noreferrer");
  await page.getByRole("button", { name: "পড়ার জন্য প্রস্তুত করুন", exact: true }).click();
  await expect(page.getByRole("link", { name: "প্রস্তুতির কাজ দেখুন →", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/source-detail-390.png", fullPage: true });
});

test("unlinked source details have a complete mobile summary", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/manage/sources/${fixture.sources.unlinked.id}/`); await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await expect(page.getByRole("heading", { name: fixture.sources.unlinked.title, exact: true })).toBeVisible();
  await expect(page.locator(".status-label")).toContainText("বইয়ের তালিকায় যুক্ত হয়নি");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
