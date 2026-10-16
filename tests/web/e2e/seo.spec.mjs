import { test, expect, fixture, canonicalOrigin } from "./fixtures.mjs";

test("home and collection structured data match the visible site and selected books", async ({ page }) => {
  await page.goto("/");
  const home = await page.locator('script[type="application/ld+json"]').allTextContents();
  expect(home.map(JSON.parse).find((item) => item["@type"] === "Organization")).toMatchObject({ name: "বাংলা পাঠাগার", url: `${canonicalOrigin}/` });
  await page.goto(`/collections/${encodeURIComponent(fixture.collection.slug)}/`);
  const markup = (await page.locator('script[type="application/ld+json"]').allTextContents()).map(JSON.parse).find((item) => item["@type"] === "CollectionPage");
  expect(markup.name).toBe(fixture.collection.name);
  const titles = await page.locator(".book-card h3").allTextContents();
  expect(markup.mainEntity.itemListElement.map((entry) => entry.item.name)).toEqual(titles);
  expect(markup.mainEntity.itemListElement.map((entry) => entry.position)).toEqual([1, 2, 3]);
});

async function sitemapLinks(page, xml) {
  return page.evaluate((value) => {
    const document = new DOMParser().parseFromString(value, "application/xml");
    return { errors: document.querySelectorAll("parsererror").length, urls: [...document.querySelectorAll("loc")].map((element) => element.textContent) };
  }, xml);
}

test("sitemap index and bounded children contain only canonical public URLs", async ({ page, request }) => {
  const index = await request.get("/sitemap.xml");
  expect(index.status()).toBe(200);
  expect(index.headers()["content-type"]).toContain("application/xml");
  const indexText = await index.text();
  const parsed = await sitemapLinks(page, indexText);
  expect(parsed.errors).toBe(0);
  expect(parsed.urls).toContain(`${canonicalOrigin}/sitemap-static.xml`);
  const books = parsed.urls.filter((value) => new URL(value).searchParams.get("kind") === "books");
  expect(books.length).toBeGreaterThan(0);
  const allBooks = new Set();
  for (const value of books) {
    const location = new URL(value), response = await request.get(`${location.pathname}${location.search}`);
    expect(response.status()).toBe(200);
    const contents = await response.text(), child = await sitemapLinks(page, contents);
    expect(child.errors).toBe(0); expect(child.urls.length).toBeGreaterThan(0); expect(child.urls.length).toBeLessThanOrEqual(1000);
    for (const privatePath of ["/manage/", "/my-books/", "/login/", "?q="]) expect(contents.includes(privatePath)).toBe(false);
    for (const url of child.urls) { expect(url.startsWith(`${canonicalOrigin}/books/`)).toBe(true); expect(allBooks.has(url)).toBe(false); allBooks.add(url); }
  }
  expect(allBooks.has(`${canonicalOrigin}/books/${encodeURIComponent(fixture.book.slug)}/`)).toBe(true);
  expect((await request.get("/sitemap-records.xml?kind=private&page=1")).status()).toBe(404);
  expect((await request.get("/sitemap-records.xml?kind=books&page=0")).status()).toBe(404);
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain(`Sitemap: ${canonicalOrigin}/sitemap.xml`);
  expect(robots).not.toContain("Disallow: /manage");
  expect(robots).not.toContain("Disallow: /_next");
  await page.goto("/catalog/?arbitrary-filter=value");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
});
