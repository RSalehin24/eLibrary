import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("private library card and table metadata keep readers within their accessible books", async ({ page }) => {
  await useAccount(page, "personal_reader");
  const slug = fixture.personal.private.slug;
  const book = await (await page.request.get(`/api/v1/me/books/${encodeURIComponent(slug)}/`)).json();
  const references = [
    { name: book.contributors[0].name, slug: book.contributors[0].slug, filter: "contributor" },
    { name: book.categories[0].name, slug: book.categories[0].slug, filter: "category" },
    { name: book.series[0].name, slug: book.series[0].slug, filter: "series" },
  ];
  expect((await page.request.get(`/contributors/${encodeURIComponent(references[0].slug)}/`)).status()).toBe(404);
  for (const layout of ["কার্ড", "ছক"]) {
    for (const reference of references) {
      await page.goto(`/my-books/?view=granted&q=${encodeURIComponent(book.title)}`);
      await page.getByRole("button", { name: layout, exact: true }).click();
      const result = layout === "কার্ড" ? page.locator(".book-card") : page.locator(".book-results-table tbody tr");
      const link = result.getByRole("link", { name: reference.name, exact: true });
      await expect(link).toBeVisible();
      const destination = new URL(await link.getAttribute("href"), page.url());
      expect(destination.pathname).toBe("/my-books/");
      expect(destination.searchParams.get("view")).toBe("granted");
      expect(destination.searchParams.get(reference.filter)).toBe(reference.slug);
      if (reference.filter === "contributor") expect(destination.searchParams.get("contributor_role")).toBe("author");
      await link.click();
      await expect(page).toHaveURL(url => url.pathname === "/my-books/" && url.searchParams.get(reference.filter) === reference.slug);
      await expect(page.locator(".book-results").getByRole("link", { name: book.title, exact: true })).toBeVisible();
      expect(new URL(page.url()).searchParams.get(reference.filter)).toBe(reference.slug);
    }
  }
});

test("direct grant-only details choose a visible related-books view and owned details retain All", async ({ page }) => {
  await useAccount(page, "personal_reader");
  const path = `/my-books/${encodeURIComponent(fixture.personal.private.slug)}/`;
  const book = await (await page.request.get(`/api/v1/me/books/${encodeURIComponent(fixture.personal.private.slug)}/`)).json();
  expect(book.library_view).toBe("granted");
  await page.goto(path);
  await page.getByRole("link", { name: "← আমার বইয়ে ফিরুন", exact: true }).click();
  await expect(page).toHaveURL(url => url.pathname === "/my-books/" && url.searchParams.get("view") === "granted");
  await expect(page.locator(".book-results").getByRole("link", { name: book.title, exact: true })).toBeVisible();
  for (const reference of [book.contributors[0], book.categories[0], book.series[0]]) {
    await page.goto(path);
    const link = page.locator(".book-detail").getByRole("link", { name: reference.name, exact: true });
    await link.click();
    await expect(page).toHaveURL(url => url.pathname === "/my-books/" && url.searchParams.get("view") === "granted");
    await expect(page.locator(".book-results").getByRole("link", { name: book.title, exact: true })).toBeVisible();
  }
  await page.goto(`/my-books/?view=granted&q=${encodeURIComponent(book.title)}`);
  const detail = page.locator(".book-results").getByRole("link", { name: book.title, exact: true });
  await expect(detail).toHaveAttribute("href", `${path}?view=granted`);
  await detail.click();
  await expect(page).toHaveURL(url => url.searchParams.get("view") === "granted");
  await useAccount(page, "reader");
  const owned = await (await page.request.get(`/api/v1/me/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
  expect(owned.library_view).toBe("all");
  await page.goto(`/my-books/${encodeURIComponent(owned.slug)}/`);
  const author = owned.contributors.find(person => person.role === "author");
  const ownedLink = page.locator(".book-detail").getByRole("link", { name: author.name, exact: true });
  const target = new URL(await ownedLink.getAttribute("href"), page.url());
  expect(target.searchParams.get("view") ?? "all").toBe("all");
});

test("delayed account actions do not move table metadata away from the reader's pointer", async ({ page }) => {
  await useAccount(page, "personal_reader");
  const book = await (await page.request.get(`/api/v1/me/books/${encodeURIComponent(fixture.personal.private.slug)}/`)).json();
  let release; const held = new Promise(resolve => { release = resolve; });
  await page.route("**/api/v1/me/book-controls/**", async route => {
    const response = await route.fetch(); await held; await route.fulfill({ response });
  });
  await page.goto(`/my-books/?view=granted&q=${encodeURIComponent(book.title)}`);
  await page.getByRole("button", { name: "ছক", exact: true }).click();
  const row = page.locator(".book-results-table tbody tr"), category = book.categories[0];
  const link = row.getByRole("link", { name: category.name, exact: true }); await expect(link).toBeVisible();
  const before = await link.boundingBox();
  release(); await expect(row.locator(".book-save-action")).toBeVisible();
  const after = await link.boundingBox();
  expect(Math.abs(after.x - before.x)).toBeLessThan(1); expect(Math.abs(after.y - before.y)).toBeLessThan(1);
  await link.click(); await expect(page).toHaveURL(url => url.searchParams.get("category") === category.slug && url.searchParams.get("view") === "granted");
});
