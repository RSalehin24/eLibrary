import { test, expect, useAccount, fixture, setLanguage } from "./fixtures.mjs";
import { newDigitalBook } from "./book-fixture.mjs";

const image = { name: "cover.png", mimeType: "image/png", buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAB4AAAAoCAIAAABmcd1FAAAAOUlEQVR4nO3QoREAIBDAsIfJGR1fj+AuGaCia848sl+FR7q8DkPCkDAkDAlDwpAwJAwJQ8KQ+HPIBWJ/ANAxERt3AAAAAElFTkSuQmCC", "base64") };

test("administrators validate, save and remove a cover in both languages", async ({ page }) => {
  const book = await newDigitalBook(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/#file-tools`);
  const file = page.getByLabel("নতুন প্রচ্ছদ", { exact: true });
  await file.setInputFiles({ name: "fake.png", mimeType: "image/png", buffer: Buffer.from("invalid image") });
  await page.getByRole("button", { name: "প্রচ্ছদ সংরক্ষণ করুন", exact: true }).click();
  await expect(file).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#book-cover-error")).toBeVisible();
  await file.setInputFiles(image);
  const saved = page.waitForResponse(response => response.url().endsWith("/cover/") && response.request().method() === "POST");
  await page.getByRole("button", { name: "প্রচ্ছদ সংরক্ষণ করুন", exact: true }).click();
  const result = await saved; expect(result.status()).toBe(200);
  const metadata = await result.json();
  expect(metadata.state).toBe("draft"); expect(metadata.cover_url).toBeTruthy();
  expect((await page.request.get(metadata.cover_url)).status()).toBe(200);
  await expect(file).toHaveValue("");
  await setLanguage(page, "en");
  const removed = page.waitForResponse(response => response.url().endsWith("/cover/") && response.request().method() === "DELETE");
  await page.getByRole("button", { name: "Remove cover", exact: true }).click();
  expect((await removed).status()).toBe(200);
  await expect(page.getByRole("button", { name: "Remove cover", exact: true })).toBeDisabled();
  await expect(page.getByRole("status").filter({ hasText: "Downloaded files may still contain earlier information" })).toBeVisible();
});

test("uncertain cover writes retain selection and block duplicate submission", async ({ page }) => {
  const book = await newDigitalBook(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  let writes = 0;
  await page.route("**/api/v1/manage/books/*/cover/", async route => {
    writes += 1;
    await route.fulfill({ status: 503, json: { code: "storage_unavailable", detail: "Synthetic storage failure", field_errors: {} } });
  });
  await page.getByLabel("নতুন প্রচ্ছদ", { exact: true }).setInputFiles(image);
  await page.getByRole("button", { name: "প্রচ্ছদ সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator("#book-cover").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(page.getByRole("button", { name: "প্রচ্ছদ সংরক্ষণ করুন", exact: true })).toBeDisabled();
  await expect(page.getByLabel("নতুন প্রচ্ছদ", { exact: true })).toHaveValue(/cover\.png$/);
  expect(writes).toBe(1);
});

test("metadata grants cannot upload covers through a direct multipart request", async ({ page }) => {
  await useAccount(page, "editor");
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post(`/api/v1/manage/books/${encodeURIComponent(fixture.book.slug)}/cover/`, {
    headers: { "X-CSRFToken": session.csrf_token },
    multipart: { expected_updated_at: new Date().toISOString(), image },
  });
  expect(response.status()).toBe(404);
});
