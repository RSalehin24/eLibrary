import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount as authenticatePage } from "./fixtures.mjs";

async function newDigitalBook(page) {
  await authenticatePage(page, "administrator");
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post("/api/v1/manage/books/", {
    headers: { "X-CSRFToken": session.csrf_token },
    data: { operation_id: randomUUID(), title: `আপলোডের পরীক্ষা ${randomUUID()}`, record_type: "digital" },
  });
  expect(response.status()).toBe(201);
  return response.json();
}

test("manual EPUB upload validates files and exposes the preparation controls", async ({ page }) => {
  const book = await newDigitalBook(page);
  const download = await page.request.get(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/download/`);
  expect(download.status()).toBe(200);
  const buffer = await download.body();
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/#book-upload`);
  const file = page.getByLabel("বইয়ের EPUB ফাইল", { exact: true });
  const submit = page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true });
  await file.setInputFiles({ name: "invalid.epub", mimeType: "application/epub+zip", buffer: Buffer.from("invalid archive") });
  await submit.click();
  await expect(page.locator("#book-upload").getByRole("alert").filter({ hasText: "সঠিক EPUB ফাইল" })).toBeVisible();
  await expect(submit).toBeEnabled();
  await file.setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer });
  await submit.click();
  await expect(page.locator("#book-upload").getByRole("status")).toContainText("EPUB আপলোড হয়েছে");
  await expect(file).toHaveValue("");
  await page.getByRole("button", { name: "পড়ার জন্য প্রস্তুত করুন", exact: true }).click();
  const operation = page.getByRole("link", { name: "প্রস্তুতির কাজ দেখুন →", exact: true });
  await expect(operation).toBeVisible(); await operation.click();
  await expect(page.getByRole("heading", { name: "কাজের অবস্থা", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: book.title, exact: true })).toBeVisible();
  await expect(page.locator(".job-detail")).toContainText("পড়ার জন্য EPUB প্রস্তুত");
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
  await expect(page.getByRole("button", { name: "বর্তমান তথ্য খুলুন", exact: true })).toBeVisible();
});

test("unfinished metadata prevents uploading over the draft", async ({ page }) => {
  const book = await newDigitalBook(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await page.getByLabel("বইয়ের EPUB ফাইল", { exact: true }).setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: Buffer.from("synthetic upload") });
  await page.getByLabel("সংক্ষিপ্ত পরিচিতি", { exact: true }).fill("অসম্পূর্ণ পরিচিতি");
  await expect(page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true })).toBeDisabled();
  await expect(page.getByText("আপলোডের আগে বইয়ের অসম্পূর্ণ তথ্য সংরক্ষণ করুন।", { exact: true })).toBeVisible();
  await expect(page.getByLabel("সংক্ষিপ্ত পরিচিতি", { exact: true })).toHaveValue("অসম্পূর্ণ পরিচিতি");
});
