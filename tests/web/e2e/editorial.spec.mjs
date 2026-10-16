import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("editorial changes require review and publish with canonical redirects", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.editorial_book.slug)}/`);
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill(`${fixture.editorial_book.title} সংশোধিত`);
  await page.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true }).fill("পর্যালোচিত মৌলিক সম্পাদকীয় বর্ণনা।");
  await page.getByLabel("সার্চের শিরোনাম (ঐচ্ছিক)").fill("সম্পাদিত বইয়ের বিশেষ শিরোনাম");
  await page.getByLabel("সার্চের বর্ণনা (ঐচ্ছিক)").fill("যাচাইকৃত প্রকাশনা ও বইয়ের পরিচিতি।");
  await page.getByLabel("সার্চ ইঞ্জিনে দেখানোর অনুমতি", { exact: true }).check();
  await expect(page.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন" })).toBeDisabled();
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(page).toHaveURL(/%E0%A6%B8%E0%A6%82%E0%A6%B6%E0%A7%8B%E0%A6%A7%E0%A6%BF%E0%A6%A4\/$/);
  await expect(page.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন" }).click();
  await expect(page.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "প্রকাশ করুন", exact: true }).click();
  await page.getByRole("link", { name: "প্রকাশিত পরিচিতি দেখুন →" }).click();
  await expect(page.getByText("পর্যালোচিত মৌলিক সম্পাদকীয় বর্ণনা।", { exact: true })).toBeVisible();
  await expect(page).toHaveTitle(/সম্পাদিত বইয়ের বিশেষ শিরোনাম/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "index, follow");
  const old = await page.request.get(`/books/${encodeURIComponent(fixture.editorial_book.slug)}/`, { maxRedirects: 0 });
  expect(old.status()).toBe(308);
  expect(old.headers().location).toContain("%E0%A6%B8%E0%A6%82%E0%A6%B6");
});

test("stale editorial form shows a conflict without replaying the update", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.conflict_book.slug)}/`);
  const otherPage = await page.context().newPage();
  await otherPage.goto(`/manage/books/${encodeURIComponent(fixture.conflict_book.slug)}/`);
  await otherPage.getByLabel("সংক্ষিপ্ত পরিচিতি", { exact: true }).fill("অন্য ফর্মের নতুন তথ্য।");
  await otherPage.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(otherPage.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" })).toBeDisabled();
  await page.getByLabel("সংক্ষিপ্ত পরিচিতি", { exact: true }).fill("পুরোনো ফর্মের তথ্য।");
  let updates = 0;
  page.on("request", (request) => { if (request.method() === "PATCH") updates += 1; });
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(page.locator(".editorial-workspace").getByRole("alert")).toContainText("বইটির তথ্য বদলেছে");
  expect(updates).toBe(1);
  await otherPage.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন" }).click();
  await expect(otherPage.getByText("পর্যালোচনা: অনুমোদিত", { exact: false })).toBeVisible();
  await otherPage.close();
});
