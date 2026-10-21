import { test, expect, fixture } from "./fixtures.mjs";

test("public catalog and metadata work without JavaScript", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await context.newPage();
  const response = await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  expect(response.status()).toBe(200);
  await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "bn");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/books\//);
  const scripts = await page.locator('script[type="application/ld+json"]').allTextContents();
  const markup = scripts.map((script) => JSON.parse(script)).find((entry) => entry["@type"] === "Book");
  expect(markup["@type"]).toBe("Book");
  expect(markup.name).toBe(fixture.book.title);
  await page.goto(`/catalog/?q=${fixture.query}`);
  await expect(page.getByRole("link", { name: "পরের পাতা", exact: true })).toHaveAttribute("href", /page=2/);
  expect(new URL(await page.getByRole("link", { name: "পরের পাতা", exact: true }).getAttribute("href"), baseURL).searchParams.has("record_type")).toBe(false);
  await page.getByRole("link", { name: "পরের পাতা", exact: true }).click();
  await expect(page).toHaveURL(url => url.searchParams.get("page") === "2" && url.searchParams.get("q") === fixture.query);
  await expect(page.locator(".book-card")).toHaveCount(3);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
  await context.close();
});

test("missing books and invalid catalog pages return 404", async ({ request }) => {
  expect((await request.get("/books/nonexistent-foundation-book/")).status()).toBe(404);
  expect((await request.get("/catalog/?page=0")).status()).toBe(404);
  expect((await request.get("/catalog/?page=1&page=2")).status()).toBe(404);
  expect((await request.get("/catalog/?q=!!!")).status()).toBe(404);
});

test("search on page two requests page one after the query changes", async ({ page }) => {
  await page.goto(`/catalog/?q=${fixture.query}&page=2`);
  const search = page.waitForResponse((response) => response.url().includes("/api/v1/catalog/books/")
    && new URL(response.url()).searchParams.get("q") === "অন্য বই");
  await page.getByLabel("বই বা লেখকের নাম", { exact: true }).fill("অন্য বই");
  const response = await search;
  expect(new URL(response.url()).searchParams.get("page")).toBe("1");
  await expect(page.getByRole("heading", { name: "কোনো বই পাওয়া যায়নি" })).toBeVisible();
  await expect(page.getByRole("link", { name: "আগের পাতা", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "পরের পাতা", exact: true })).toHaveCount(0);
});

test("public contributor and category pages provide ordinary paginated links", async ({ page }) => {
  await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  await page.locator('a[href^="/contributors/"][href$="?role=author"]').click();
  await expect(page.locator(".book-card")).toHaveCount(24);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
  await page.getByRole("link", { name: "পরের পাতা", exact: true }).click();
  await expect(page.locator(".book-card")).toHaveCount(1);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\?page=2$/);
  await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  await page.locator('a[href^="/categories/"]').click();
  await expect(page.locator(".book-card")).toHaveCount(24);
});

test("curated collection shows reviewed introduction and editorial book order", async ({ page }) => {
  await page.goto(`/collections/${encodeURIComponent(fixture.collection.slug)}/`);
  await expect(page.getByRole("heading", { name: fixture.collection.name, exact: true })).toBeVisible();
  await expect(page.getByText("এটি স্থানীয় পরীক্ষার জন্য পর্যালোচিত তিন বইয়ের নির্বাচিত সংগ্রহ।", { exact: true })).toBeVisible();
  await expect(page.locator(".book-card")).toHaveCount(3);
  await expect(page.locator(".book-card").first()).toContainText(fixture.book.title);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "index, follow");
  await page.goto(`/collections/?q=${encodeURIComponent(fixture.collection.name)}`);
  const entry = page.locator(".entity-directory").getByRole("link").filter({ has: page.getByText(fixture.collection.name, { exact: true }) });
  await expect(entry).toBeVisible();
  await expect(entry).toContainText("৩ টি বই");
  await entry.click();
  await expect(page.getByRole("heading", { name: fixture.collection.name, exact: true })).toBeVisible();
});
