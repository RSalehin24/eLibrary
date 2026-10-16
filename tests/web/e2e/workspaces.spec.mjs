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
  await expect(page.getByRole("link", { name: "পরিচালনা", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "প্রস্থান", exact: true }).click();
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
  await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
  await expect(page.locator(".management-list>li")).toHaveCount(3);
  await expect(page.getByRole("link", { name: "পাঠকের জায়গায় যান", exact: true })).toBeVisible();
});

test("administrator profile opens the management controls and marks the active section", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/profile/");
  await expect(page.locator('.workspace-nav [aria-current="page"]')).toHaveText("প্রোফাইল");
  await page.getByRole("link", { name: "পরিচালনায় যান", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/$/);
  const shortcuts = page.getByRole("navigation", { name: "পরিচালনার প্রধান কাজ", exact: true });
  await expect(shortcuts.getByRole("link", { name: "উৎস থেকে বই আনুন", exact: false })).toHaveAttribute("href", "/manage/sources/");
  await expect(shortcuts.getByRole("link", { name: "নিজে বই যোগ করুন", exact: false })).toHaveAttribute("href", "/manage/books/new/");
  await shortcuts.getByRole("link", { name: "উৎস থেকে বই আনুন", exact: false }).click();
  await expect(page.getByRole("heading", { name: "বইয়ের উৎস", exact: true })).toBeVisible();
  await expect(page.locator('.workspace-nav [aria-current="page"]')).toHaveText("উৎস");
  await expect(page.getByRole("list", { name: "উৎস থেকে বই আনার ধাপ", exact: true }).locator("li")).toHaveCount(3);
});

test("reader profiles expose personal settings without administrative shortcuts", async ({ page }) => {
  await useAccount(page, "reader"); await page.goto("/profile/");
  await expect(page.getByRole("link", { name: "পরিচালনায় যান", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "পরিচালনা", exact: true })).toHaveCount(0);
  expect((await page.request.get("/manage/sources/")).status()).toBe(404);
});
