import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test("blocked source publication explains regeneration in both languages without replaying the request", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.conflict_book.slug)}/`);
  let requests = 0;
  await page.route("**/api/v1/manage/books/*/publish/", async route => {
    requests += 1;
    await route.fulfill({ status: 409, json: { code: "state_conflict", detail: "Regenerate the source book to verify its complete text and files.", field_errors: {} } });
  });
  await page.getByRole("button", { name: "প্রকাশ করুন", exact: true }).click();
  const alert = page.locator(".editorial-workspace").getByRole("alert");
  await expect(alert).toContainText("বইয়ের সম্পূর্ণ লেখা ও ফাইল স্বয়ংক্রিয়ভাবে যাচাই করতে বইটি আবার তৈরি করুন।");
  await expect(alert).not.toContainText("তথ্য বদলেছে");
  await setLanguage(page, "en");
  await expect(alert).toContainText("Regenerate this book to verify its complete text and files automatically.");
  expect(requests).toBe(1);
});

test("saved editorial changes publish directly with canonical redirects", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.editorial_book.slug)}/`);
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill(`${fixture.editorial_book.title} সংশোধিত`);
  await page.getByLabel("বিস্তারিত বিবরণ", { exact: true }).fill("পর্যালোচিত মৌলিক সম্পাদকীয় বর্ণনা।");
  await page.getByLabel("সার্চের শিরোনাম (ঐচ্ছিক)").fill("সম্পাদিত বইয়ের বিশেষ শিরোনাম");
  await page.getByLabel("সার্চের বর্ণনা (ঐচ্ছিক)").fill("যাচাইকৃত প্রকাশনা ও বইয়ের পরিচিতি।");
  await page.getByLabel("পরিবর্তনের কারণ (ঐচ্ছিক)", { exact: true }).fill("বইয়ের নাম ও বিবরণ সংশোধন করা হয়েছে।");
  await expect(page.locator("form.editorial-form")).toHaveCount(1);
  await expect(page.locator("#metadata-history")).toHaveCount(1);
  await page.getByLabel("সার্চ ইঞ্জিনে দেখানোর অনুমতি", { exact: true }).check();
  await expect(page.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন" })).toHaveCount(0);
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(page).toHaveURL(/%E0%A6%B8%E0%A6%82%E0%A6%B6%E0%A7%8B%E0%A6%A7%E0%A6%BF%E0%A6%A4\/$/);
  await expect(page.locator("form.editorial-form")).toHaveCount(1);
  await page.getByRole("link", { name: "তথ্যের ইতিহাস", exact: true }).click();
  const history = page.locator("#metadata-history");
  await expect(history.getByText("বইয়ের নাম ও বিবরণ সংশোধন করা হয়েছে।", { exact: true })).toBeVisible();
  await expect(history.getByText("বইয়ের তথ্য সম্পাদনা", { exact: true })).toBeVisible();
  await setLanguage(page, "en");
  await expect(page.getByRole("heading", { name: "Metadata History", exact: true })).toBeVisible();
  await expect(history.getByText("Book details edited", { exact: true })).toBeVisible();
  await setLanguage(page, "bn");

  await expect(page.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "প্রকাশ করুন", exact: true }).click();
  await page.getByRole("link", { name: "প্রকাশিত পাতা দেখুন" }).click();
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
  await otherPage.getByLabel("সংক্ষিপ্ত বিবরণ", { exact: true }).fill("অন্য ফর্মের নতুন তথ্য।");
  await otherPage.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(otherPage.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" })).toBeDisabled();
  await page.getByLabel("সংক্ষিপ্ত বিবরণ", { exact: true }).fill("পুরোনো ফর্মের তথ্য।");
  let updates = 0;
  page.on("request", (request) => { if (request.method() === "PATCH") updates += 1; });
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(page.locator(".editorial-workspace").getByRole("alert")).toContainText("বইটির তথ্য বদলেছে");
  expect(updates).toBe(1);
  await expect(otherPage.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeEnabled();
  await expect(otherPage.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন" })).toHaveCount(0);
  await otherPage.close();
});
