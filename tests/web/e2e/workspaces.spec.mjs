import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("login preserves a private deep link and logout clears access", async ({ page }) => {
  await page.goto(`/my-books/${encodeURIComponent(fixture.book.slug)}/`);
  await expect(page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ করুন" })).toBeVisible();
  await expect(page.getByLabel("দুই ধাপের নিরাপত্তা কোড", { exact: true })).toHaveCount(0);
  await page.getByLabel("ইমেইল", { exact: true }).fill(fixture.reader.email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(fixture.reader.password);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/my-books/${encodeURIComponent(fixture.book.slug)}/$`));
  await expect(page.getByRole("heading", { name: fixture.book.title, exact: true, level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: "অ্যাডমিন", exact: true })).toHaveCount(0);
  await page.locator("details.account-menu:visible > summary").click(); await page.getByRole("button", { name: "প্রস্থান", exact: true }).click();
  await page.locator("details.account-menu:visible > summary").click();
  await expect(page.getByRole("link", { name: "প্রবেশ করুন", exact: true })).toBeVisible();
  expect((await page.request.get("/api/v1/me/books/")).status()).toBe(403);
});

test("reader sees personal progress and cannot open management", async ({ page }) => {
  await useAccount(page, "reader");
  await page.goto("/my-books/");
  await expect(page.getByText("পড়া হয়েছে ৪২%", { exact: true })).toBeVisible();
  await expect(page.locator(".book-card")).toHaveCount(1);
  expect((await page.request.get("/manage/")).status()).toBe(404);
});

test("scoped editor receives only the granted management book", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto("/manage/books/");
  await expect(page.locator(".managed-books-table").getByRole("link", { name: fixture.book.title, exact: true })).toBeVisible();
  await expect(page.locator(".managed-books-table tbody tr")).toHaveCount(3);
  await expect(page.getByRole("link", { name: "পাঠকের ভিউ", exact: true })).toBeVisible();
});

test("administrator profile opens the management controls and marks the active section", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/profile/");
  await expect(page.getByRole("heading", { name: "প্রোফাইল ও নিরাপত্তা", exact:true })).toBeVisible();
  await page.getByRole("link", { name: "অ্যাডমিন প্যানেল", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/sources\/$/);
  const actions = page.locator(".source-creation-actions");
  await expect(actions.getByRole("button", { name: "সব বইয়ের তথ্য আনুন", exact: true })).toBeVisible();
  await expect(actions.getByRole("link", { name: "EPUB আপলোড", exact: true })).toHaveAttribute("href", "/manage/books/new/");
  await expect(page.getByRole("heading", { name: "বই তৈরি", exact: true })).toBeVisible();
  await expect(page.locator('.admin-desktop-navigation .workspace-nav [aria-current="page"]')).toHaveText("বই তৈরি");
  await expect(page.getByRole("button", { name: "সব বইয়ের তথ্য আনুন", exact: true })).toBeVisible();
  await page.getByLabel("বই বা লেখকের নাম", { exact: true }).fill(fixture.sources.query);
  await page.getByRole("search").getByRole("button", { name: "খুঁজুন", exact: true }).click();
  await page.locator('.source-row input[type="checkbox"]:not([disabled])').first().check();
  await expect(page.getByRole("button", { name: /নির্বাচিত বই তৈরি করুন/, exact: false })).toBeEnabled();
});

test("reader profiles expose personal settings without administrative shortcuts", async ({ page }) => {
  await useAccount(page, "reader"); await page.goto("/profile/");
  await expect(page.getByRole("link", { name: "অ্যাডমিন প্যানেল", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "অ্যাডমিন", exact: true })).toHaveCount(0);
  expect((await page.request.get("/manage/sources/")).status()).toBe(404);
});
