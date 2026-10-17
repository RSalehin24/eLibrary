import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("a processor starts and controls source discovery from a narrow workspace", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/manage/sources/?q=${fixture.sources.query}`);
  await expect(page.getByRole("heading", { name: "বই তৈরি", exact: true })).toBeVisible();
  await page.getByLabel("সর্বোচ্চ পাতা", { exact: true }).fill("2");
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const response = page.waitForResponse((entry) => entry.url().endsWith("/sources/discovery/") && entry.request().method() === "POST");
  await page.getByRole("button", { name: "কয়েকটি পাতা আনুন", exact: true }).click();
  expect((await response).status()).toBe(202);
  await page.locator(".source-sync").getByRole("link", { name: "কাজের বিস্তারিত", exact: true }).click();
  await expect(page.getByRole("heading", { name: "বইয়ের তালিকা সংগ্রহ", exact: true })).toBeVisible();
  await expect(page.locator(".status-label")).toContainText("অপেক্ষমাণ");
  await page.getByRole("button", { name: "স্থগিত করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("স্থগিত");
  await page.getByRole("button", { name: "বাতিল করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("বাতিল");
});
