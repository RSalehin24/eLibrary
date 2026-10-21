import { test, expect, fixture, useAccount, artifactPath, setLanguage } from "./fixtures.mjs";

test("book details retain every contributor role and personal related-book links", async ({ page }) => {
  await useAccount(page, "reader");
  const book = await (await page.request.get(`/api/v1/catalog/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
  const translator = book.contributors.find(person => person.role === "translator");
  const editor = book.contributors.find(person => person.role === "editor");
  await page.goto(`/books/${encodeURIComponent(book.slug)}/`);
  await expect(page.locator(".book-facts").getByText("অনুবাদক", { exact: true })).toBeVisible();
  await expect(page.locator(".book-facts").getByRole("link", { name: translator.name, exact: true })).toHaveAttribute("href", `/contributors/${encodeURIComponent(translator.slug)}/?role=translator`);
  await expect(page.locator(".book-facts").getByRole("link", { name: editor.name, exact: true })).toBeVisible();
  await page.goto(`/my-books/${encodeURIComponent(book.slug)}/`);
  const related = page.locator(".book-facts").getByRole("link", { name: translator.name, exact: true });
  await related.click();
  await expect(page).toHaveURL(url => url.pathname === "/my-books/" && url.searchParams.get("contributor_role") === "translator");
  const parameters = new URL(page.url()).searchParams;
  expect(new URL(page.url()).pathname).toBe("/my-books/");
  expect(parameters.get("contributor")).toBe(translator.slug);
  expect(parameters.get("contributor_role")).toBe("translator");
  await expect(page.getByRole("heading", { name: book.title, exact: true })).toBeVisible();
});

test("protected detail previews restore dedication and nested contents in both languages", async ({ page }) => {
  await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  await expect(page.locator(".book-detail-preview")).toHaveCount(0);
  const denied = await page.request.get(`/api/v1/reading/books/${encodeURIComponent(fixture.book.slug)}/details/`);
  expect(denied.status()).toBe(403);
  await useAccount(page, "reader");
  await page.reload();
  const preview = page.locator(".book-detail-preview");
  await expect(preview.getByRole("heading", { name: "উৎসর্গ", exact: true })).toBeVisible();
  await expect(preview).toContainText("পাঠকদের জন্য উৎসর্গ।");
  await expect(preview.getByRole("heading", { name: "সূচিপত্র", exact: true })).toBeVisible();
  await expect(preview.locator(".book-detail-contents li")).toHaveCount(9);
  await setLanguage(page, "en");
  await expect(preview.getByRole("heading", { name: "Dedication", exact: true })).toBeVisible();
  await expect(preview.getByRole("heading", { name: "Publication Details", exact: true })).toBeVisible();
  await expect(preview.locator("dt").getByText("First Published", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  for (const value of await page.locator(".book-detail .book-facts dd").all()) {
    expect((await value.boundingBox()).width).toBeGreaterThan(160);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: artifactPath(`book-details-${test.info().project.name}.png`), fullPage: true });
  await page.goto(`/my-books/${encodeURIComponent(fixture.book.slug)}/`);
  await expect(page.locator(".book-detail-preview")).toContainText("পাঠকদের জন্য উৎসর্গ।");
});
