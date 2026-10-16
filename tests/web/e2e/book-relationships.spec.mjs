import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

async function chooseReference(page, label, name) {
  await page.getByLabel(`${label}: নাম খুঁজুন`, { exact: true }).fill(name);
  const selector = page.getByLabel(`${label}: যোগ করুন`, { exact: true });
  await expect(selector).toBeEnabled();
  await expect(selector.getByRole("option", { name, exact: true })).toHaveCount(1);
  await selector.selectOption({ label: name });
}

async function createBook(page, title) {
  const token = (await (await page.request.get("/api/v1/auth/session/")).json()).csrf_token;
  const response = await page.request.post("/api/v1/manage/books/", { headers: { "X-CSRFToken": token }, data: { operation_id: randomUUID(), title, record_type: "manual" } });
  expect(response.status()).toBe(201); return response.json();
}

async function createReference(page, kind, name) {
  const token = (await (await page.request.get("/api/v1/auth/session/")).json()).csrf_token;
  const response = await page.request.post(`/api/v1/manage/entities/${kind}/`, { headers: { "X-CSRFToken": token }, data: { operation_id: randomUUID(), name } });
  expect(response.status()).toBe(201); return response.json();
}

test("book relationships preserve contributor roles and link explicit editions", async ({ page }) => {
  await useAccount(page, "catalog_administrator"); await page.setViewportSize({ width: 320, height: 800 });
  const book = await createBook(page, `সম্পর্কের বই ${randomUUID()}`);
  const sibling = await createBook(page, `অন্য সংস্করণ ${randomUUID()}`);
  const contributor = await createReference(page, "contributors", `সম্পর্কের সহযোগী ${randomUUID()}`);
  const category = await createReference(page, "categories", `সম্পর্কের বিভাগ ${randomUUID()}`);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await page.getByRole("link", { name: "বইয়ের সম্পর্ক ও সংস্করণ সম্পাদনা করুন", exact: true }).click();
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await chooseReference(page, "সহযোগী", contributor.name);
  await page.getByLabel("যোগ করার ভূমিকা", { exact: true }).selectOption("translator");
  await chooseReference(page, "সহযোগী", contributor.name);
  await chooseReference(page, "বিভাগ", category.name);
  await chooseReference(page, "অন্য সংস্করণ", sibling.title);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/book-relationships-320.png", fullPage: true });
  await page.getByRole("button", { name: "বইয়ের সম্পর্ক সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "বইয়ের সম্পর্ক সংরক্ষিত হয়েছে" })).toBeVisible();
  const relationships = (await (await page.request.get(`/api/v1/manage/books/${encodeURIComponent(book.slug)}/relationships/`)).json());
  expect(relationships.contributors.map((entry) => entry.role)).toEqual(["author", "translator"]);
  expect(relationships.categories[0].id).toBe(category.id);
  expect(relationships.related_editions.map((entry) => entry.id)).toEqual([sibling.id]);
  await page.getByRole("button", { name: "এই বইটি সংস্করণদল থেকে সরান", exact: true }).click();
  await page.getByRole("button", { name: "বইয়ের সম্পর্ক সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "বইয়ের সম্পর্ক সংরক্ষিত হয়েছে" })).toBeVisible();
  const detached = await (await page.request.get(`/api/v1/manage/books/${encodeURIComponent(book.slug)}/relationships/`)).json();
  expect(detached.group_id).toBeNull(); expect(detached.related_editions).toEqual([]);
});

test("relationship administration excludes scoped editors", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`/manage/books/${encodeURIComponent(fixture.book.slug)}/`);
  await expect(page.getByRole("link", { name: "বইয়ের সম্পর্ক ও সংস্করণ সম্পাদনা করুন", exact: true })).toHaveCount(0);
  expect((await page.request.get(`/manage/books/${encodeURIComponent(fixture.book.slug)}/relationships/`)).status()).toBe(404);
});

test("a newly created contributor refreshes cached relationship search results", async ({ page }) => {
  await useAccount(page, "catalog_administrator");
  const book = await createBook(page, `নতুন সহযোগীর বই ${randomUUID()}`), name = `নতুন সহযোগী ${randomUUID()}`;
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/relationships/`);
  await page.getByLabel("সহযোগী: নাম খুঁজুন", { exact: true }).fill(name);
  const selection = page.getByLabel("সহযোগী: যোগ করুন", { exact: true });
  await expect(selection).toBeEnabled();
  await expect(selection.getByRole("option")).toHaveCount(1);
  await page.getByRole("link", { name: "পরিচিতি", exact: true }).click();
  await page.getByRole("link", { name: "লেখক ও সহযোগী", exact: true }).click();
  await page.getByRole("link", { name: "পরিচিতি তৈরি করুন", exact: true }).click();
  await page.getByLabel("নাম", { exact: true }).fill(name);
  await page.getByRole("button", { name: "পরিচিতি তৈরি করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "পরিচিতি তৈরি হয়েছে", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "বই", exact: true }).click();
  await page.getByRole("link", { name: book.title, exact: true }).click();
  await page.getByRole("link", { name: "বইয়ের সম্পর্ক ও সংস্করণ সম্পাদনা করুন", exact: true }).click();
  await chooseReference(page, "সহযোগী", name);
  await expect(page.locator(".reference-selection").getByText(`${name} · লেখক`, { exact: true })).toBeVisible();
});
