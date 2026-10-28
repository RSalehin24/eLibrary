import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("catalog managers enter ordinary bibliographic metadata on phones without assigning ownership", async ({ page }) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/manage/books/"); await page.getByRole("link", { name: "বই যোগ করুন", exact: true }).click();
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  const title = `বই ${randomUUID()}`;
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill(title);
  await page.getByLabel("সংস্করণ", { exact: true }).fill("দ্বিতীয় সংস্করণ");
  await page.getByLabel("প্রকাশক", { exact: true }).fill("পরীক্ষার প্রকাশক");
  await page.getByLabel("সংকলন বই", { exact: true }).check();
  await expect(page.locator('select[name="record_type"], input[name="manual_price"], select[name="manual_binding"]')).toHaveCount(0);
  const button = page.getByRole("button", { name: "বই যোগ করুন", exact: true });
  expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(44);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/catalog-create-320.png", fullPage: true });
  const saved = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/api/v1/manage/books/"));
  await button.click(); const response = await saved; expect(response.status()).toBe(201); const book = await response.json();
  expect(book.state).toBe("draft"); expect(book.indexing_eligible).toBe(false);
  await expect(page.getByRole("heading", { name: "বই যোগ হয়েছে", exact: true })).toBeVisible();
  expect((await (await page.request.get(`/api/v1/me/books/?q=${encodeURIComponent(title)}`)).json()).entries).toEqual([]);
  await page.getByRole("link", { name: "বইয়ের তথ্য সম্পাদনা করুন", exact: true }).click();
  await expect(page.getByLabel("প্রকাশক", { exact: true })).toHaveValue("পরীক্ষার প্রকাশক");
  await page.getByLabel("সংস্করণ", { exact: true }).fill("তৃতীয় সংস্করণ");
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
  const status = `/manage/book-creations/${book.id}/`;
  const statusPage = await page.context().newPage();
  try {
    await statusPage.setViewportSize(page.viewportSize()); await statusPage.goto(status);
    await expect(statusPage.getByRole("heading", { name: "বই যোগ হয়েছে", exact: true })).toBeVisible();
    await expect(statusPage.getByText(title, { exact: true })).toBeVisible();
  } finally { await statusPage.close(); }
  await useAccount(page, "catalog_administrator");
  expect((await (await page.request.get("/api/v1/auth/session/")).json()).user.id).toBe(fixture.catalog_administrator.id);
  expect((await page.request.get(`/api/v1/manage/book-creations/${book.id}/`)).status()).toBe(404);
  expect((await page.request.get(status)).status()).toBe(404);
});

test("creation rejects scoped editors and reader accounts", async ({ page }) => {
  for (const account of ["editor", "reader"]) {
    await useAccount(page, account);
    expect((await page.request.get("/manage/books/new/")).status()).toBe(404);
    const token = (await (await page.request.get("/api/v1/auth/session/")).json()).csrf_token;
    const response = await page.request.post("/api/v1/manage/books/", {
      headers: { "X-CSRFToken": token }, data: { operation_id: randomUUID(), title: "অনুমতি ছাড়া বই" },
    });
    expect(response.status()).toBe(403);
  }
  await useAccount(page, "editor"); await page.goto("/manage/books/");
  await expect(page.getByRole("link", { name: "বই যোগ করুন", exact: true })).toHaveCount(0);
});

test("creation validates fields and never replays an uncertain command", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/manage/books/new/");
  const button = page.getByRole("button", { name: "বই যোগ করুন", exact: true });
  await button.click(); await expect(page.getByLabel("বইয়ের নাম", { exact: true })).toHaveAttribute("aria-invalid", "true");
  await expect(button).toBeEnabled(); const writes = [];
  await page.route("**/api/v1/manage/books/", async (route) => {
    writes.push(route.request().postDataJSON()); await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain creation", field_errors: {} }) });
  });
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill(`অনিশ্চিত অনুরোধ ${fixture.query}`); await button.click();
  await expect(page.locator(".editorial-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(button).toBeDisabled(); expect(writes).toHaveLength(1);
  await expect(page.getByRole("link", { name: "এই অনুরোধের ফল দেখুন", exact: true })).toHaveAttribute("href", `/manage/book-creations/${writes[0].operation_id}/`);
});
