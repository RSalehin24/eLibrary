import { test, expect } from "./fixtures.mjs";
import { newDigitalBook, readingEPUB } from "./book-fixture.mjs";

test("manual EPUB upload validates files and automatically prepares the reader", async ({ page }) => {
  const book = await newDigitalBook(page);
  const buffer = await readingEPUB(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/#book-upload`);
  const file = page.getByLabel("বইয়ের EPUB ফাইল", { exact: true });
  const submit = page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true });
  await file.setInputFiles({ name: "invalid.epub", mimeType: "application/epub+zip", buffer: Buffer.from("invalid archive") });
  const rejected = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/epub/"));
  await submit.click();
  expect((await rejected).status()).toBe(400);
  await expect(page.locator("#book-upload").getByRole("alert").filter({ hasText: "সঠিক EPUB ফাইল" })).toBeVisible();
  await expect(submit).toBeEnabled();
  await file.setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer });
  await submit.click();
  await expect(page.locator("#book-upload").getByRole("status").filter({ hasText: "EPUB পরীক্ষা করে পড়ার জন্য প্রস্তুত করা হয়েছে" })).toBeVisible();
  await expect(file).toHaveValue("");
  await expect(page.locator("#book-files")).toContainText("অনলাইনে পড়ার জন্য প্রস্তুত");
  await expect(page.getByRole("button", { name: "পড়ার জন্য প্রস্তুত করুন", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "বই পড়ুন", exact: true }).click();
  await expect(page).toHaveURL(/\/reader\/[^/]+\/$/);
  await expect(page.frameLocator(".reader-frame").locator("body")).toContainText(/বাংলা/);
});

test("uncertain uploads retain the selected file and are never replayed", async ({ page }) => {
  const book = await newDigitalBook(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  const writes = [];
  await page.route("**/api/v1/manage/books/*/epub/", async (route) => {
    writes.push(route.request());
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic upload failure", field_errors: {} }) });
  });
  await page.getByLabel("বইয়ের EPUB ফাইল", { exact: true }).setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: Buffer.from("synthetic upload") });
  const submit = page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true });
  await submit.click();
  await expect(page.locator("#book-upload").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(submit).toBeDisabled(); expect(writes).toHaveLength(1);
  await expect(page.getByLabel("বইয়ের EPUB ফাইল", { exact: true })).toHaveValue(/book\.epub$/);
  await expect(page.getByRole("button", { name: "আবার খুলুন", exact: true })).toBeVisible();
});

test("unfinished metadata prevents uploading over the draft", async ({ page }) => {
  const book = await newDigitalBook(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await page.getByLabel("বইয়ের EPUB ফাইল", { exact: true }).setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: Buffer.from("synthetic upload") });
  await page.getByLabel("সংক্ষিপ্ত বিবরণ", { exact: true }).fill("অসম্পূর্ণ পরিচিতি");
  await expect(page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true })).toBeDisabled();
  await expect(page.getByText("আপলোডের আগে বইয়ের পরিবর্তনগুলো সংরক্ষণ করুন।", { exact: true })).toBeVisible();
  await expect(page.getByLabel("সংক্ষিপ্ত বিবরণ", { exact: true })).toHaveValue("অসম্পূর্ণ পরিচিতি");
});
