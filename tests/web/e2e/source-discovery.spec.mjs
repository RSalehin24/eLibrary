import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("a processor starts and controls source discovery from a narrow workspace", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/manage/sources/?q=${fixture.sources.query}`);
  await expect(page.getByRole("heading", { name: "নতুন উৎস আবিষ্কার", exact: true })).toBeVisible();
  await page.getByLabel("সর্বোচ্চ কত পাতা সংগ্রহ হবে", { exact: true }).fill("2");
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const response = page.waitForResponse((entry) => entry.url().endsWith("/sources/discovery/") && entry.request().method() === "POST");
  await page.getByRole("button", { name: "উৎসের পরিচিতি সংগ্রহ করুন", exact: true }).click();
  expect((await response).status()).toBe(202);
  await page.getByRole("link", { name: "উৎস আবিষ্কারের কাজ দেখুন →", exact: true }).click();
  await expect(page.getByRole("heading", { name: "বইয়ের উৎস আবিষ্কার", exact: true })).toBeVisible();
  await expect(page.locator(".status-label")).toContainText("অপেক্ষমাণ");
  await page.getByRole("button", { name: "স্থগিত করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("স্থগিত");
  await page.getByRole("button", { name: "বাতিল করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("বাতিল");
});
