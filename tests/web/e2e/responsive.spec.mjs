import { test, expect, fixture, useAccount } from "./fixtures.mjs";

for (const width of [320, 375, 390, 768, 820, 1024, 1366, 1920]) {
  test(`public and private workspaces fit ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/catalog/?q=${fixture.query}`);
    await expect(page.getByRole("heading", { name: "সব বই", exact: true })).toBeVisible();
    await expect(page.locator(".book-grid")).toHaveCSS("display", "grid");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await useAccount(page, "kindle_reader");
    await page.goto(`/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
    await expect(page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/kindle-composer-${width}.png`, fullPage: true });
    await useAccount(page, "editor");
    await page.goto("/manage/books/");
    await expect(page.getByRole("heading", { name: "সব বই", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.locator("details.account-menu:visible > summary").click();
    const button = await page.getByRole("button", { name: "প্রস্থান", exact: true }).boundingBox();
    expect(button.height).toBeGreaterThanOrEqual(44);
    await page.keyboard.press("Escape");
    if (width === 390 || width === 1366) await page.screenshot({ path: `test-artifacts/foundation/manage-${width}.png`, fullPage: true });
    await page.goto(`/manage/books/${encodeURIComponent(fixture.book.slug)}/`);
    await expect(page.getByLabel("বিস্তারিত বিবরণ", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (width === 390 || width === 1366) await page.screenshot({ path: `test-artifacts/foundation/editorial-${width}.png`, fullPage: true });
    await page.goto("/profile/");
    await expect(page.getByLabel("নাম", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/profile-${width}.png`, fullPage: true });
    await useAccount(page, "administrator"); await page.goto("/manage/jobs/");
    await expect(page.getByRole("heading", { name: "কাজের অবস্থা", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await useAccount(page, "access_manager"); await page.goto(`/manage/users-access/${fixture.managed_reader.id}/`);
    await expect(page.getByRole("button", { name: "অ্যাকাউন্ট সংরক্ষণ করুন", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/access-management-${width}.png`, fullPage: true });
    await page.goto("/manage/users-access/invite/");
    await expect(page.getByRole("button", { name: "আমন্ত্রণ পাঠান", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/invitation-form-${width}.png`, fullPage: true });
    await page.goto("/manage/overview/");
    await expect(page.getByRole("heading", { name: "আমন্ত্রণের ইমেইল", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/overview-${width}.png`, fullPage: true });
    await useAccount(page, "source_processor"); await page.goto(`/manage/sources/?q=${fixture.sources.query}`);
    await expect(page.getByRole("heading", { name: "বই তৈরি", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test("rotation and text enlargement preserve accessible navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/help/");
  await page.setViewportSize({ width: 844, height: 390 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("link", { name: "বই খুঁজুন", exact: true })).toBeVisible();
});

test("private account and job actions remain usable with enlarged text at 320 pixels", async ({ page }) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 320, height: 800 });
  for (const path of ["/profile/", "/manage/", "/manage/jobs/", `/manage/jobs/${fixture.preparation_job.id}/`, `/manage/users-access/${fixture.managed_reader.id}/`]) {
    await page.goto(path); await page.addStyleTag({ content: "html { font-size: 200%; }" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.locator("details.account-menu:visible > summary").click();
    await expect(page.getByRole("button", { name: "প্রস্থান", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
  }
  await useAccount(page, "kindle_reader"); await page.goto(`/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true })).toBeVisible();
});
