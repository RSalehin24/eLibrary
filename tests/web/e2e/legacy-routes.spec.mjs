import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("legacy library and writer links retain validated filters", async ({ page }) => {
  await page.goto(`/library/?q=${encodeURIComponent(fixture.query)}&sort=title&next=https://attacker.test`);
  await expect(page).toHaveURL(/\/catalog\/\?/);
  const target = new URL(page.url());
  expect(target.searchParams.get("q")).toBe(fixture.query);
  expect(target.searchParams.get("sort")).toBe("title");
  expect(target.searchParams.get("record_type")).toBe("digital");
  expect(target.searchParams.has("next")).toBe(false);
  await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
  await page.goto("/translators/");
  await expect(page).toHaveURL(/\/contributors\/\?role=translator$/);
  await expect(page.getByLabel("ভূমিকা", { exact: true })).toHaveValue("translator");
});

test("old administration routes retain authorization and old reader links discard external manifests", async ({ page }) => {
  await page.goto("/access/");
  await expect(page).toHaveURL(/\/login\/\?next=/);
  expect(decodeURIComponent(new URL(page.url()).searchParams.get("next"))).toBe("/manage/users-access/");
  await useAccount(page, "reading_reader");
  await page.goto(`/reader/?slug=${encodeURIComponent(fixture.reading_book.slug)}&manifest=https://attacker.test/fake`);
  await expect(page).toHaveURL(new RegExp(`/my-books/${encodeURIComponent(fixture.reading_book.slug)}/$`));
  await expect(page.getByRole("heading", { name: fixture.reading_book.title, exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "বই পড়ুন", exact: true }).or(page.getByRole("link", { name: "পড়া চালিয়ে যান", exact: true }))).toBeVisible();
  await page.goto("/access/");
  await expect(page.getByRole("heading", { name: "পাতাটি পাওয়া যায়নি", exact: true })).toBeVisible();
});

test("legacy multi-page contents links open the corresponding authorized processing view", async ({ page }) => {
  await useAccount(page, "administrator");
  for (const route of ["multipage-toc", "processing-multi-page-toc"]) {
    await page.goto(`/${route}/`);
    const destination = new URL(page.url());
    expect(destination.pathname).toBe("/manage/jobs/");
    expect(destination.searchParams.get("kind")).toBe("process_source");
    expect(destination.searchParams.get("layout")).toBe("multi_page");
    await expect(page.locator("select[name=layout]")).toHaveValue("multi_page");
  }
  await page.goto("/__proto__/");
  await expect(page.getByRole("heading", { name: "পাতাটি পাওয়া যায়নি", exact: true })).toBeVisible();
});
