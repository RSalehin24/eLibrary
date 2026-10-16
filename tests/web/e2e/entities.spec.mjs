import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

async function createEntity(page, kind, name) {
  await page.goto(`/manage/entities/${kind}/new/`);
  await page.getByLabel("নাম", { exact: true }).fill(name);
  await page.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true }).fill("পর্যালোচনার জন্য মৌলিক সম্পাদকীয় পরিচিতি।");
  await page.getByLabel("সার্চ ইঞ্জিনে দেখানোর অনুমতি", { exact: true }).check();
}

async function selectBook(page, title) {
  await page.getByLabel("নির্বাচিত বই: নাম খুঁজুন", { exact: true }).fill(title);
  const selector = page.getByLabel("নির্বাচিত বই: যোগ করুন", { exact: true });
  await expect(selector).toBeEnabled();
  await expect(selector.getByRole("option", { name: title, exact: true })).toHaveCount(1);
  await selector.selectOption({ label: title });
}

test("managers create edit search and review all four entity kinds", async ({ page }) => {
  await useAccount(page, "catalog_administrator");
  for (const kind of ["contributors", "categories", "series", "collections"]) {
    const name = `সম্পাদিত পরিচিতি ${randomUUID()}`;
    await createEntity(page, kind, name);
    await page.getByRole("button", { name: "পরিচিতি তৈরি করুন", exact: true }).click();
    await expect(page.getByRole("heading", { name: "পরিচিতি তৈরি হয়েছে", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "তথ্য সম্পাদনা ও পর্যালোচনা করুন", exact: true }).click();
    await page.getByLabel("যাচাইকৃত বিকল্প নাম (প্রতি লাইনে একটি, সর্বোচ্চ ২০টি)", { exact: true }).fill(`alternative ${name}`);
    await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
    await page.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন", exact: true }).click();
    await expect(page.getByText("পর্যালোচনা: অনুমোদিত", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "← তালিকায় ফিরুন", exact: true }).click();
    await page.getByLabel("নাম বা বিকল্প নাম খুঁজুন", { exact: true }).fill(`alternative ${name}`);
    await page.getByRole("button", { name: "খুঁজুন", exact: true }).click();
    await expect(page.locator(".management-list").getByRole("link", { name, exact: true })).toBeVisible();
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  }
});

test("collection selection persists order and publishes on a narrow screen", async ({ page }) => {
  await useAccount(page, "catalog_administrator");
  await page.setViewportSize({ width: 320, height: 800 });
  await createEntity(page, "collections", `নতুন নির্বাচিত বই ${randomUUID()}`);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await selectBook(page, fixture.book.title);
  await selectBook(page, fixture.reading_book.title);
  await page.getByRole("button", { name: `${fixture.reading_book.title}: আগে নিন`, exact: true }).click();
  expect(await page.locator('.reference-selection input[type="hidden"]').evaluateAll((inputs) => inputs.map((input) => input.value))).toHaveLength(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/entity-collection-320.png", fullPage: true });
  const created = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/api/v1/manage/entities/collections/"));
  await page.getByRole("button", { name: "পরিচিতি তৈরি করুন", exact: true }).click();
  const data = await (await created).json();
  expect(data.selected_books.map((book) => book.name)).toEqual([fixture.reading_book.title, fixture.book.title]);
  await page.getByRole("link", { name: "তথ্য সম্পাদনা ও পর্যালোচনা করুন", exact: true }).click();
  await expect(page.locator(".reference-selection li")).toHaveCount(2);
  await page.getByRole("button", { name: "পর্যালোচনা অনুমোদন করুন", exact: true }).click();
  await expect(page.getByRole("button", { name: "প্রকাশ করুন", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "প্রকাশ করুন", exact: true }).click();
  await page.getByRole("link", { name: "প্রকাশিত পরিচিতি দেখুন →", exact: true }).click();
  await expect(page.getByRole("heading", { name: data.name, exact: true })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "index, follow");
  const titles = await page.locator(".book-card h3").allTextContents();
  expect(titles).toEqual([fixture.reading_book.title, fixture.book.title]);
});

test("scoped editors see their granted entities and readers cannot manage them", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto("/manage/entities/contributors/");
  await expect(page.locator(".management-list li")).toHaveCount(1);
  await page.getByRole("link", { name: fixture.entities.contributor.name, exact: true }).click();
  await page.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true }).fill("সীমিত লেখকের পরিচিতি");
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
  expect((await page.request.get("/manage/entities/contributors/new/")).status()).toBe(404);
  await useAccount(page, "reader");
  expect((await page.request.get(`/manage/entities/contributors/${fixture.entities.contributor.id}/`)).status()).toBe(404);
});

test("entity conflicts preserve drafts and block uncertain repeated writes", async ({ page }) => {
  await useAccount(page, "catalog_administrator");
  await createEntity(page, "series", `সমান্তরাল সিরিজ ${randomUUID()}`);
  await page.getByRole("button", { name: "পরিচিতি তৈরি করুন", exact: true }).click();
  await page.getByRole("link", { name: "তথ্য সম্পাদনা ও পর্যালোচনা করুন", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/entities\/series\/[0-9a-f-]+\/$/);
  const other = await page.context().newPage(); await other.goto(page.url());
  await other.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true }).fill("অন্য সম্পাদকের সংরক্ষিত লেখা");
  await other.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
  await expect(other.locator(".editorial-workspace").getByRole("status")).toContainText("পরিবর্তন সংরক্ষিত হয়েছে");
  await page.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true }).fill("আমার অসম্পূর্ণ খসড়া");
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".editorial-workspace").getByRole("alert")).toContainText("তথ্যটি অন্য জায়গায় বদলেছে");
  await expect(page.getByLabel("সম্পাদকীয় বর্ণনা", { exact: true })).toHaveValue("আমার অসম্পূর্ণ খসড়া");
  await expect(page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true })).toBeDisabled();
  await other.close();
});

test("entity creation validates fields and retains the uncertain request identifier", async ({ page }) => {
  await useAccount(page, "catalog_administrator"); await page.goto("/manage/entities/categories/new/");
  const button = page.getByRole("button", { name: "পরিচিতি তৈরি করুন", exact: true });
  await button.click(); await expect(page.getByLabel("নাম", { exact: true })).toHaveAttribute("aria-invalid", "true");
  await expect(button).toBeEnabled(); let request;
  await page.route("**/api/v1/manage/entities/categories/", async (route) => {
    request = route.request().postDataJSON(); await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain creation", field_errors: {} }) });
  });
  await page.getByLabel("নাম", { exact: true }).fill("অনিশ্চিত বিভাগ"); await button.click();
  await expect(page.locator(".editorial-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(button).toBeDisabled();
  await expect(page.getByRole("link", { name: "এই অনুরোধের বর্তমান পরিচিতি দেখুন →", exact: true })).toHaveAttribute("href", `/manage/entities/categories/${request.operation_id}/`);
});
