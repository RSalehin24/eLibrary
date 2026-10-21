import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

async function english(page) {
  await setLanguage(page, "en");
}

test("administrators can open all books from the public catalog and search visible book cards", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.goto("/catalog/"); await english(page);
  await expect(page.locator(".site-header")).toHaveAttribute("data-workspace", "admin");
  const navigation = page.locator(".site-header").getByRole("navigation", { name: "Admin navigation", exact: true });
  await navigation.getByRole("link", { name: "All Books", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/books\/$/);
  expect((await page.getByRole("search").getByRole("searchbox").boundingBox()).height).toBeGreaterThanOrEqual(44);
  const book = await (await page.request.get(`/api/v1/catalog/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
  await page.getByRole("search").getByRole("searchbox").fill(book.catalog_code);
  await page.getByRole("search").getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".managed-books-table tbody tr")).toHaveCount(1);
  const card = page.locator(".managed-books-table tbody tr");
  await expect(card.getByRole("link", { name: fixture.book.title, exact: true })).toBeVisible();
  await expect(card.locator('.book-cover')).toBeVisible();
  await expect(card.getByRole("link", { name: "Edit", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("the author landing page lists records immediately and opens their related books", async ({ page }) => {
  await useAccount(page, "catalog_administrator");
  await page.goto("/manage/entities/"); await english(page);
  await expect(page.locator(".entity-results li").first()).toBeVisible();
  await page.getByRole("search").getByRole("searchbox").fill(fixture.entities.contributor.name);
  await page.getByRole("search").getByRole("button", { name: "Search", exact: true }).click();
  const row = page.locator(".entity-results li");
  await expect(row).toHaveCount(1);
  await expect(row.getByRole("heading")).toHaveText(fixture.entities.contributor.name);
  if ((await page.viewportSize()).width >= 900) expect((await row.boundingBox()).height).toBeLessThan(90);
  await row.getByRole("link", { name: "View Books", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/books\/\?contributor=/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(fixture.entities.contributor.name);
  await expect(page.locator(".catalog-filter-summary").getByRole("link", { name: "View All Books", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /review/i })).toHaveCount(0);
});

test("public author and category links lead to the matching books and preserve author roles", async ({ page }) => {
  await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`); await english(page);
  const author = page.locator('main a[href^="/contributors/"]').first();
  const path = await author.getAttribute("href");
  await page.goto("/contributors/?role=author");
  await expect(page.locator(".entity-directory li").first()).toBeVisible();
  await expect(page.locator(".entity-directory li a").first()).toHaveAttribute("href", /\?role=author$/);
  await page.goto(path);
  await expect(page.locator(".book-card")).toHaveCount(24);
  await page.getByRole("link", { name: "Next Page", exact: true }).click();
  await expect(page.locator(".book-card").filter({ has: page.getByRole("heading", { name: fixture.book.title, exact: true }) })).toBeVisible();
  await page.goto("/categories/");
  await expect(page.locator(".entity-directory li").first()).toBeVisible();
  expect((await page.request.get("/contributors/not-a-real-author/?role=invalid")).status()).toBe(404);
});

test("adding a book puts it in the default My Books list and removal persists", async ({ page }) => {
  await useAccount(page, "personal_reader");
  const book = fixture.personal.edition;
  await page.goto(`/books/${encodeURIComponent(book.slug)}/`); await english(page);
  await page.getByRole("button", { name: "Add to My Books", exact: true }).click();
  await expect(page.getByRole("button", { name: "Remove from My Books", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "View My Books", exact: true }).click();
  await expect(page).toHaveURL(/\/my-books\/$/);
  await expect(page.getByRole("heading", { name: book.title, exact: true })).toBeVisible();
  await page.goto(`/books/${encodeURIComponent(book.slug)}/`);
  await page.getByRole("button", { name: "Remove from My Books", exact: true }).click();
  await expect(page.getByRole("button", { name: "Add to My Books", exact: true })).toBeVisible();
  await page.goto("/my-books/");
  await expect(page.getByRole("heading", { name: book.title, exact: true })).toHaveCount(0);
  await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`);
  await expect(page.getByRole("button", { name: "Add to My Books", exact: true })).toHaveCount(1);
});

test("Kindle and Notes navigation have icons and unfinished books have their own source scope", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.goto("/my-books/"); await english(page);
  await page.locator(".site-header").getByRole("link", { name:"Reader View",exact:true }).click();
  for (const name of ["Kindle", "Notes"]) {
    await expect(page.locator(".primary-navigation").getByRole("link", { name, exact: true }).locator("svg")).toBeVisible();
  }
  await page.goto("/manage/unfinished/");
  await expect(page.getByRole("heading", { level: 1, name: "Unfinished Books", exact: true })).toBeVisible();
  await expect(page.getByText("Books marked unfinished by the source website.", { exact: false })).toBeVisible();
  await expect(page.locator('input[name="catalog_scope"]')).toHaveValue("unfinished");
  await expect(page.getByRole("button", { name: "Fetch All", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
