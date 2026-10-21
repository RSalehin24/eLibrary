import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test("catalog page numbers expose real boundaries and preserve filters when jumping", async ({ page }) => {
  const sample=fixture.pagination;
  expect(sample.page_count).toBe(10);
  await page.goto(`/catalog/?q=${encodeURIComponent(sample.query)}&page=5&sort=title`);
  const pagination=page.locator(".numbered-pagination");
  await expect(pagination.locator('[aria-current="page"]:visible')).toHaveText("৫");
  await expect(pagination.getByRole("link",{name:"পাতা ১০",exact:true})).toBeVisible();
  expect(new URL(await pagination.getByRole("link",{name:"পাতা ১০",exact:true}).getAttribute("href"), page.url()).searchParams.has("record_type")).toBe(false);
  await pagination.getByRole("link",{name:"পাতা ১০",exact:true}).click();
  await expect(page).toHaveURL(/page=10/);
  expect(new URL(page.url()).searchParams.get("q")).toBe(sample.query);
  expect(new URL(page.url()).searchParams.get("sort")).toBe("title");
  await expect(page.locator('.numbered-pagination [aria-current="page"]:visible')).toHaveText("১০");
  await expect(page.locator(".numbered-pagination").getByRole("link",{name:"পরের পাতা",exact:true})).toHaveCount(0);
});

test("management page numbers fit phone screens and remain bilingual", async ({ page }) => {
  await useAccount(page,"administrator"); await page.setViewportSize({width:320,height:900});
  await page.goto("/manage/users-access/?page=2");
  const pagination=page.locator(".numbered-pagination");
  await expect(pagination.locator('[aria-current="page"]:visible')).toHaveText("২");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await setLanguage(page, "en");
  await expect(pagination.locator('[aria-current="page"]:visible')).toHaveText("2");
  await pagination.getByRole("link",{name:"Previous Page",exact:true}).click();
  await expect(page).toHaveURL(/page=1/);
});

test("nonexistent personal and paper-book pages never claim the library is empty", async ({ page }) => {
  await useAccount(page,"reader");
  for(const path of ["/my-books/?page=9999","/physical-books/?page=9999"]) expect((await page.request.get(path)).status()).toBe(404);
});
