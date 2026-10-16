import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("a processor creates and edits a schedule on a phone without granting reader controls", async ({ page }) => {
  await useAccount(page, "source_processor");
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/manage/automations/new/");
  await expect(page.getByRole("heading", { name: "নতুন সময়সূচি", exact: true })).toBeVisible();
  const name = `নিয়মিত সংগ্রহ ${fixture.query}`;
  await page.getByLabel("সময়সূচির নাম", { exact: true }).fill(name);
  await page.getByLabel("প্রথমবার চলার স্থানীয় তারিখ", { exact: true }).fill("2035-01-31");
  await page.getByLabel("প্রথমবার চলার স্থানীয় সময়", { exact: true }).fill("08:30");
  await page.getByLabel("কত দিন পরপর চলবে", { exact: true }).selectOption("monthly");
  await page.getByLabel("একবারে উৎসের সর্বোচ্চ পাতা", { exact: true }).fill("2");
  await page.getByLabel("সংগৃহীত উৎস থেকে সর্বোচ্চ কতটি বই প্রস্তুত হবে", { exact: true }).fill("3");
  await page.getByLabel("সময়সূচি সক্রিয়", { exact: true }).check();
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/automation-form-320.png", fullPage: true });
  await page.getByRole("button", { name: "সময়সূচি সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "চলার ইতিহাস", exact: true })).toBeVisible();
  await expect(page.getByText("এখনও এই সময়সূচি থেকে কোনো কাজ শুরু হয়নি।", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 1366, height: 900 });
  await page.screenshot({ path: "test-artifacts/foundation/automation-detail-1366.png", fullPage: true });
  await page.setViewportSize({ width: 320, height: 800 });
  await page.getByLabel("সময়সূচি সক্রিয়", { exact: true }).uncheck();
  const update = page.waitForResponse((response) => response.url().includes("/manage/automations/") && response.request().method() === "PATCH");
  await page.getByRole("button", { name: "সময়সূচি সংরক্ষণ করুন", exact: true }).click();
  expect((await update).status()).toBe(200);
  await page.reload();
  await expect(page.getByLabel("সময়সূচি সক্রিয়", { exact: true })).not.toBeChecked();
  await page.getByRole("link", { name: "← সময়সূচিতে ফিরুন", exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
});

test("reader accounts cannot view schedules or automation navigation", async ({ page }) => {
  await useAccount(page, "reader");
  const response = await page.goto("/manage/automations/");
  expect(response.status()).toBe(404);
  await expect(page.getByRole("link", { name: "স্বয়ংক্রিয় কাজ", exact: true })).toHaveCount(0);
});
