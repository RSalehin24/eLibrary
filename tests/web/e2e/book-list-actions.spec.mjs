import { test, expect, fixture, useAccount, artifactPath, setLanguage } from "./fixtures.mjs";

test("catalog and personal card/table lists expose save and permitted Kindle controls with one batch read", async ({ page }) => {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const slug = fixture.reading_book.slug;
  await page.request.put(`/api/v1/me/books/${encodeURIComponent(slug)}/saved/`, { headers, data: { saved: false } });
  const reads = [];
  page.on("request", request => { if (request.method() === "GET" && /(?:book-controls|\/saved\/)/.test(request.url())) reads.push(request.url()); });
  try {
    await page.goto(`/catalog/?q=${encodeURIComponent(fixture.reading_book.title)}`);
    await setLanguage(page, "en");
    const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: fixture.reading_book.title, exact: true }) });
    await expect(card.getByRole("link", { name: "Send to Kindle", exact: true })).toHaveAttribute("href", `/kindle/books/${encodeURIComponent(slug)}/`);
    await card.getByRole("button", { name: "Add to My Books", exact: true }).click();
    await expect(card.getByRole("button", { name: "Remove from My Books", exact: true })).toBeVisible();
    expect(reads.filter(url => url.includes("/saved/"))).toHaveLength(0);
    expect(reads.filter(url => url.includes("book-controls" )).length).toBeLessThanOrEqual(2);
    await page.getByRole("button", { name: "Table", exact: true }).click();
    const row = page.getByRole("row").filter({ has: page.getByRole("rowheader", { name: fixture.reading_book.title, exact: true }) });
    await expect(row.getByRole("button", { name: "Remove from My Books", exact: true })).toBeVisible();
    await expect(row.getByRole("link", { name: "Send to Kindle", exact: true })).toBeVisible();
    await page.goto(`/my-books/?view=saved&q=${encodeURIComponent(fixture.reading_book.title)}`);
    await expect(page.getByRole("button", { name: "Remove from My Books", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Remove from My Books", exact: true }).click();
    await expect(page.getByRole("heading", { name: fixture.reading_book.title, exact: true })).toHaveCount(0);
    await page.goto("about:blank"); await useAccount(page, "personal_reader");
    await page.goto(`/catalog/?q=${encodeURIComponent(fixture.book.title)}`);
    await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
    const ungranted = page.getByRole("article").filter({ has: page.getByRole("heading", { name: fixture.book.title, exact: true }) });
    await expect(ungranted.getByRole("button", { name: "Add to My Books", exact: true })).toBeVisible();
    await expect(ungranted.getByRole("link", { name: "Send to Kindle", exact: true })).toHaveCount(0);
    await page.goto(`/my-books/?q=${encodeURIComponent(fixture.personal.paper.title)}`);
    await expect(page.getByRole("heading", { name: fixture.personal.paper.title, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Send to Kindle", exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: artifactPath(`list-actions-${test.info().project.name}.png`), fullPage: true });
  } finally {
    await useAccount(page, "reading_reader");
    await page.request.put(`/api/v1/me/books/${encodeURIComponent(slug)}/saved/`, { headers, data: { saved: false } });
  }
});
