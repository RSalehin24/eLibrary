import { test, expect, fixture, artifactPath, setLanguage } from "./fixtures.mjs";

test("contributor directories default to authors and clean retired query constraints", async ({ page }) => {
  const book = await (await page.request.get(`/api/v1/catalog/books/${encodeURIComponent(fixture.book.slug)}/`)).json();
  const author = book.contributors.find(person => person.role === "author");
  const response = await page.request.get(`/api/v1/catalog/entities/contributors/?q=${encodeURIComponent(author.name)}`);
  expect(response.status()).toBe(200);
  const record = (await response.json()).entries.find(entry => entry.id === author.id);
  const date = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Dhaka" }).format(new Date(record.created_at));
  await page.goto(`/contributors/?q=${encodeURIComponent(author.name)}&sort=-catalog_code&created_after=${date}&created_before=${date}&page=2`);
  await expect(page).toHaveURL(url => url.pathname === "/contributors/" && url.searchParams.get("sort") === "-catalog_code" && !url.searchParams.has("created_after") && !url.searchParams.has("created_before") && !url.searchParams.has("page"));
  await setLanguage(page, "en");
  await expect(page.locator('input[type="date"], select[name="record_type"]')).toHaveCount(0);
  await expect(page.locator('select[name="role"]')).toHaveValue("author");
  const result = page.locator(".entity-directory li").filter({ hasText: author.name });
  await expect(result).not.toContainText(record.catalog_code);
  await expect(result).not.toContainText("Dhaka");
  await page.getByLabel("Sort list", { exact: true }).selectOption("created_at");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(url => url.searchParams.get("sort") === "created_at" && !url.searchParams.has("created_after"));
  await expect(result.getByRole("link")).toHaveAttribute("href", `/contributors/${encodeURIComponent(author.slug)}/?role=author`);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: artifactPath(`entity-directory-${test.info().project.name}.png`), fullPage: true });
});

test("all directories remove unwanted controls while legacy API validation remains intact", async ({ page }) => {
  for (const path of ["/contributors/", "/categories/", "/series/", "/collections/"]) {
    await page.goto(`${path}?record_type=manual&created_after=2026-02-30`);
    await expect(page).toHaveURL(url => url.pathname === path && !url.searchParams.has("record_type") && !url.searchParams.has("created_after"));
    await expect(page.locator('input[type="date"], select[name="record_type"]')).toHaveCount(0);
    await expect(page.locator('select[name="sort"] option[value="-created_at"]')).toHaveCount(1);
  }
  expect((await page.request.get("/api/v1/catalog/entities/collections/?sort=catalog_code")).status()).toBe(400);
  expect((await page.request.get("/api/v1/catalog/entities/contributors/?created_after=2026-02-30")).status()).toBe(400);
  expect((await page.request.get("/api/v1/catalog/entities/contributors/?created_after=2026-10-21&created_before=2026-10-20")).status()).toBe(400);
});
