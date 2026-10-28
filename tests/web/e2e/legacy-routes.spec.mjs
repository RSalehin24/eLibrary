import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("retired library and contributor aliases are absent", async ({ page }) => {
  for (const route of ["library", "writers", "translators", "editors", "publishers"]) {
    const response = await page.goto(`/${route}/?q=${encodeURIComponent(fixture.query)}&next=https://attacker.test`);
    expect(response.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "পাতাটি পাওয়া যায়নি", exact: true })).toBeVisible();
  }
});

test("reader entry retains the authorized destination and discards external manifests", async ({ page }) => {
  expect((await page.request.get("/access/")).status()).toBe(404);
  await useAccount(page, "reading_reader");
  await page.goto(`/reader/?slug=${encodeURIComponent(fixture.reading_book.slug)}&manifest=https://attacker.test/fake`);
  await expect(page).toHaveURL(new RegExp(`/my-books/${encodeURIComponent(fixture.reading_book.slug)}/$`));
  await expect(page.getByRole("heading", { name: fixture.reading_book.title, exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "বই পড়ুন", exact: true }).or(page.getByRole("link", { name: "পড়া চালিয়ে যান", exact: true }))).toBeVisible();
  expect((await page.request.get("/access/")).status()).toBe(404);
});

test("retired processing aliases and unknown routes return not found", async ({ page }) => {
  await useAccount(page, "administrator");
  for (const route of ["multipage-toc", "processing-multi-page-toc", "__proto__"]) {
    expect((await page.goto(`/${route}/`)).status()).toBe(404);
    await expect(page.getByRole("heading", { name: "পাতাটি পাওয়া যায়নি", exact: true })).toBeVisible();
  }
});
