import { test, expect, useAccount, setLanguage } from "./fixtures.mjs";

test("notification sounds require opt-in, persist muted settings and preserve a single accessible result", async ({ page }, testInfo) => {
  await page.addInitScript(() => {
    window.notificationAudio = { created: 0, tones: [] };
    window.AudioContext = class {
      constructor() { window.notificationAudio.created += 1; this.state = "running"; this.currentTime = 0; this.destination = {}; }
      resume() { return Promise.resolve(); }
      close() { this.state = "closed"; return Promise.resolve(); }
      createOscillator() {
        let frequency = 0;
        return { frequency: { setValueAtTime(value) { frequency = value; } }, connect() {}, disconnect() {}, start() { window.notificationAudio.tones.push(frequency); }, stop() {} };
      }
      createGain() { return { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {}, disconnect() {} }; }
    };
  });
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  const sounds = page.getByRole("checkbox", { name: "নোটিফিকেশনের শব্দ চালু রাখুন" });
  await expect(sounds).not.toBeChecked();
  expect(await page.evaluate(() => window.notificationAudio.created)).toBe(0);
  await sounds.check();
  await expect(sounds).toBeChecked();
  expect(await page.evaluate(() => window.notificationAudio.tones)).toEqual([]);
  await page.getByLabel("নাম", { exact: true }).fill("Notification feedback reader");
  await page.getByRole("button", { name: "নাম সংরক্ষণ করুন", exact: true }).click();
  const notification = page.getByTestId("notifications");
  await expect(notification.getByRole("status")).toContainText("পরিবর্তন সংরক্ষিত হয়েছে।");
  await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে।" })).toHaveCount(1);
  await expect.poll(() => page.evaluate(() => window.notificationAudio.tones)).toEqual([660, 880]);
  await page.screenshot({ path: testInfo.outputPath("notification-completion.png") });
  await page.getByRole("button", { name: "বার্তা বন্ধ করুন", exact: true }).click();
  await expect(notification.getByRole("status")).toHaveCount(0);
  await page.route("**/api/v1/auth/profile/", (route) => route.request().method() === "PATCH" ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Temporarily unavailable", field_errors: {} }) }) : route.continue());
  await page.getByLabel("নাম", { exact: true }).fill("Unsent notification reader");
  await page.getByRole("button", { name: "নাম সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".account-settings").getByRole("alert")).toHaveCount(1);
  await expect(notification.getByRole("alert")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.notificationAudio.tones)).toEqual([660, 880, 260, 196]);
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Unsent notification reader");
  await page.unroute("**/api/v1/auth/profile/");
  await page.getByRole("button", { name: "লেখা বাদ দিন", exact: true }).click();
  await page.reload();
  await expect(sounds).toBeChecked();
  expect(await page.evaluate(() => window.notificationAudio.created)).toBe(0);
  await sounds.uncheck();
  await page.getByLabel("নাম", { exact: true }).fill("Muted notification reader");
  await page.getByRole("button", { name: "নাম সংরক্ষণ করুন", exact: true }).click();
  await expect(notification.getByRole("status")).toContainText("পরিবর্তন সংরক্ষিত হয়েছে।");
  expect(await page.evaluate(() => window.notificationAudio.tones)).toEqual([]);
  await page.reload(); await expect(sounds).not.toBeChecked();
  await setLanguage(page, "en");
  await expect(page.getByRole("heading", { name: "Notification sounds", exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Enable notification sounds", exact: true })).not.toBeChecked();
  await page.getByRole("heading", { name: "Notification sounds", exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("notification-settings.png") });
});
