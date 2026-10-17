import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { newDigitalBook, readingEPUB } from "./book-fixture.mjs";

test("job workspace rejects readers and metadata-only editors", async ({ page }) => {
  await useAccount(page, "reader");
  expect((await page.request.get("/manage/jobs/")).status()).toBe(404);
  expect((await page.request.get(`/api/v1/manage/jobs/${fixture.preparation_job.id}/`)).status()).toBe(403);
  await useAccount(page, "editor"); await page.goto("/manage/books/");
  await expect(page.locator(".workspace-nav").getByRole("link", { name: "প্রসেসিং", exact: true })).toHaveCount(0);
  expect((await page.request.get("/manage/jobs/")).status()).toBe(404);
});

test("invalid and missing job pages return 404", async ({ page }) => {
  await useAccount(page, "administrator");
  for (const query of ["page=0", "page=0x10", "page=1e2", "page=9999999", "page=1&page=2", "state=__proto__", "state=missing"]) expect((await page.request.get(`/manage/jobs/?${query}`)).status()).toBe(404);
  expect((await page.request.get("/manage/jobs/00000000-0000-0000-0000-000000000000/")).status()).toBe(404);
  expect((await page.request.get("/catalog/?page=0x10")).status()).toBe(404);
});

test("phone job details support pause resume and cancellation with confirmed states", async ({ page }) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/manage/jobs/${fixture.preparation_job.id}/`);
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  for (const [action, state] of [["স্থগিত করুন", "স্থগিত"], ["আবার চালু করুন", "অপেক্ষমাণ"], ["বাতিল করুন", "বাতিল"]]) {
    const button = page.getByRole("button", { name: action, exact: true });
    expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(44);
    await button.click(); await expect(page.locator(".status-label")).toHaveText(state);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/job-detail-390.png", fullPage: true });
  await page.goto("/manage/jobs/?state=cancelled");
  await expect(page.getByRole("heading", { name: fixture.reading_book.title, exact: true })).toBeVisible();
});

test("asset preparation returns a trackable command and conflicts are not replayed", async ({ page }) => {
  const book = await newDigitalBook(page), bytes = await readingEPUB(page);
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await page.getByLabel("বইয়ের EPUB ফাইল", { exact: true }).setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: bytes });
  await page.getByRole("button", { name: "EPUB আপলোড করুন", exact: true }).click();
  await expect(page.locator("#book-upload").getByRole("status").filter({ hasText: "EPUB আপলোড হয়েছে" })).toBeVisible();
  await page.getByRole("button", { name: "পড়ার জন্য প্রস্তুত করুন", exact: true }).click();
  const link = page.getByRole("link", { name: "প্রস্তুতির কাজ দেখুন", exact: true });
  await expect(link).toBeVisible(); await link.click();
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  const controls = [];
  await page.route("**/api/v1/manage/jobs/*/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    controls.push(route.request());
    await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "state_conflict", detail: "Synthetic revision conflict", field_errors: {} }) });
  });
  await page.getByRole("button", { name: "স্থগিত করুন", exact: true }).click();
  await expect(page.locator(".job-detail").getByRole("alert")).toContainText("কাজের অবস্থাটি বদলেছে");
  await expect(page.getByRole("button", { name: "স্থগিত করুন", exact: true })).toBeDisabled();
  expect(controls).toHaveLength(1);
});

test("job polling suspends when hidden and does not overlap slow reads", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/manage/jobs/");
  let releaseRead; const pending = new Promise((resolve) => { releaseRead = resolve; });
  const reads = [];
  await page.route("**/api/v1/manage/jobs/?*", async (route) => { reads.push(route.request()); await pending; await route.continue(); });
  await expect.poll(() => reads.length).toBe(1);
  await page.waitForTimeout(2_100);
  expect(reads).toHaveLength(1);
  releaseRead();
  await page.evaluate(() => { Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" }); window.dispatchEvent(new Event("visibilitychange")); });
  const stoppedCount = reads.length;
  await page.waitForTimeout(2_100);
  expect(reads).toHaveLength(stoppedCount);
});

test("catalog results expose empty historical syncs, failures and the next creation step in both languages", async ({ page }) => {
  await useAccount(page, "administrator");
  const path = `/api/v1/manage/jobs/${fixture.preparation_job.id}/`;
  const original = await (await page.request.get(path)).json();
  let job = { ...original, kind: "discover_source", state: "succeeded", stage: "source_catalog_discovered",
    book: null, source_record: null, discovered_pages: 1, discovered_entries: 0, more_pages_available: false, error_code: "", actions: [] };
  await page.route(`**${path}`, (route) => route.request().method() === "GET" ? route.fulfill({ json: job }) : route.abort());
  await page.goto(`/manage/jobs/${fixture.preparation_job.id}/`);
  for (const language of ["English", "বাংলা"]) {
    await page.getByRole("button", { name: language, exact: true }).click();
    const english = language === "English";
    const refresh = page.getByRole("button", { name: english ? "Refresh Status" : "অবস্থা হালনাগাদ করুন", exact: true });
    job = { ...job, state: "succeeded", discovered_entries: 0, error_code: "" };
    await refresh.click();
    await expect(page.locator(".status-label")).toHaveText(english ? "No Books Found" : "কোনো বই পাওয়া যায়নি");
    await expect(page.locator(".discovery-result").getByRole("alert")).toBeVisible();
    await expect(page.locator(".discovery-result a")).toHaveAttribute("href", "/manage/sources/");
    job = { ...job, state: "failed", error_code: "source_catalog_layout_unrecognized" };
    await refresh.click();
    await expect(page.locator(".job-detail .field-error")).toContainText(english ? "no recognizable book listing" : "বইয়ের তালিকা শনাক্ত করা যায়নি");
    job = { ...job, state: "succeeded", discovered_entries: 60, error_code: "" };
    await refresh.click();
    await expect(page.locator(".discovery-result").getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("link", { name: english ? "Choose Books to Create" : "বই বেছে নিয়ে তৈরি করুন", exact: true })).toBeVisible();
  }
});
