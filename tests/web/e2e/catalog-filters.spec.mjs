import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount, artifactPath, setLanguage } from "./fixtures.mjs";

test("combined filters sort real books and saved views survive navigation", async ({ page }) => {
  await useAccount(page, "personal_reader");
  const book = await (await page.request.get(`/api/v1/catalog/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
  const author = book.contributors.find(person => person.role === "author").name;
  const category = book.categories[0].name;
  await page.goto(`/catalog/?q=${fixture.query}`);
  await setLanguage(page, "en");
  const form = page.locator(".catalog-filters-form");
  await form.getByRole("button", { name: "Filters", exact: true }).click();
  await form.getByLabel("Author or contributor", { exact: true }).fill(author);
  await form.getByLabel("Category", { exact: true }).fill(category);
  await form.getByLabel("Sort books", { exact: true }).selectOption("title");
  await form.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/contributor=/);
  await expect(page.locator(".book-card").first()).toBeVisible();
  const parameters = new URL(page.url()).searchParams;
  expect(parameters.get("contributor")).toBe(author);
  expect(parameters.get("category")).toBe(category);
  expect(parameters.get("sort")).toBe("title");
  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(page.locator(".book-results-table tbody tr").first()).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Book Title", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cards", exact: true }).click();
  const name = `Saved ${randomUUID()}`;
  let identifier;
  try {
    await page.locator(".saved-catalog-filters > summary").click();
    await page.getByLabel("Filter name", { exact: true }).fill(name);
    const created = page.waitForResponse((response) => response.url().includes("/me/saved-filters/") && response.request().method() === "POST");
    await page.locator(".saved-filter-create").getByRole("button", { name: "Save", exact: true }).click();
    const response = await created;
    expect(response.status()).toBe(201); identifier = (await response.json()).id;
    await expect(page.locator(".saved-filter-list").getByRole("link", { name, exact: true })).toBeVisible();
    await page.locator(".catalog-filters-form").getByRole("link", { name: "Clear filters", exact: true }).click();
    await expect(page).toHaveURL(url => !url.searchParams.get("contributor") && !url.searchParams.get("q"));
    await page.locator(".saved-catalog-filters > summary").click();
    await page.locator(".saved-filter-list").getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(url => url.searchParams.get("contributor") === author && url.searchParams.get("sort") === "title");
    await expect(page.locator('input[name="contributor"]')).toHaveValue(author);
    await expect(page.locator('select[name="sort"]')).toHaveValue("title");
    await page.locator(".catalog-filter-details > summary").click();
    await page.locator(".saved-catalog-filters > summary").click();
    await page.getByRole("button", { name: `${name}: Delete saved filter`, exact: true }).click();
    await expect(page.locator(".saved-filter-list").getByRole("link", { name, exact: true })).toHaveCount(0);
    identifier = undefined;
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: artifactPath(`catalog-filters-${test.info().project.name}.png`), fullPage: true });
  } finally {
    if (identifier) {
      const session = await (await page.request.get("/api/v1/auth/session/")).json();
      await page.request.delete(`/api/v1/me/saved-filters/${identifier}/`, { headers: { "X-CSRFToken": session.csrf_token } });
    }
  }
});

test("combined filter controls and catalog results work without JavaScript", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
  try {
    const page = await context.newPage();
    const book = await (await page.request.get(`/api/v1/catalog/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
    const author = book.contributors.find(person => person.role === "author").name;
    await page.goto(`/catalog/?q=${fixture.query}`);
    const form = page.locator(".catalog-filters-form");
    await form.locator("summary").click();
    await form.locator('input[name="contributor"]').fill(author);
    await form.locator('select[name="sort"]').selectOption("title");
    await form.getByRole("button", { name: "খুঁজুন", exact: true }).click();
    await expect(page.locator(".book-card").first()).toBeVisible();
    expect(new URL(page.url()).searchParams.get("contributor")).toBe(author);
    await expect(form.locator('select[name="sort"]')).toHaveValue("title");
  } finally { await context.close(); }
});

test("My Books tabs preserve selected filters and filtered empty results are clear", async ({ page }) => {
  await useAccount(page, "personal_reader");
  await page.goto("/my-books/?sort=title&record_type=manual");
  await setLanguage(page, "en");
  await page.locator("main .workspace-nav").getByRole("link", { name: "Saved", exact: true }).click();
  await expect(page.locator("main .workspace-nav").getByRole("link", { name: "Saved", exact: true })).toHaveAttribute("aria-current", "page");
  expect(new URL(page.url()).searchParams.get("sort")).toBe("title");
  expect(new URL(page.url()).searchParams.has("record_type")).toBe(false);
  await expect(page.locator('select[name="record_type"]')).toHaveCount(0);
  await page.goto("/catalog/?contributor=unknown-nonexistent-author");
  await expect(page.getByRole("heading", { name: "No Books Found", exact: true })).toBeVisible();
  await expect(page.getByText("Change the filters or use fewer conditions and search again.", { exact: true })).toBeVisible();
});
