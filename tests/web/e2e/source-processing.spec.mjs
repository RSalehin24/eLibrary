import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("an unlinked source accepts one trackable processing request", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.goto(`/manage/sources/${fixture.sources.unlinked.id}/`);
  const accepted = page.waitForResponse((response) => response.url().endsWith(`/sources/${fixture.sources.unlinked.id}/process/`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "এই উৎস প্রক্রিয়ার অনুরোধ করুন", exact: true }).click();
  expect((await accepted).status()).toBe(202);
  await page.getByRole("link", { name: "কাজের অবস্থা দেখুন →", exact: true }).click();
  await expect(page.getByRole("heading", { name: fixture.sources.unlinked.title, exact: true })).toBeVisible();
  await expect(page.locator(".status-label")).toContainText("অপেক্ষমাণ");
  await page.getByRole("link", { name: "উৎসের তথ্য দেখুন →", exact: true }).click();
  await expect(page.getByRole("link", { name: "চলমান কাজ ও করণীয় দেখুন →", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "এই উৎস প্রক্রিয়ার অনুরোধ করুন", exact: true })).toHaveCount(0);
});

test("a stale duplicate decision preserves its draft and is never replayed", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.goto(`/manage/jobs/${fixture.source_processing.duplicate}/`);
  await page.getByLabel("করণীয় নির্বাচন করুন", { exact: true }).selectOption("link");
  await page.getByLabel("সংযুক্ত করার বই", { exact: true }).selectOption(fixture.source_processing.candidate);
  let writes = 0;
  await page.route(`**/api/v1/manage/jobs/${fixture.source_processing.duplicate}/source-issue/`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    writes += 1; await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "state_conflict", detail: "The candidate changed.", field_errors: {} }) });
  });
  await page.getByRole("button", { name: "সিদ্ধান্ত সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "তথ্যটি অন্য জায়গায় বদলেছে" })).toBeVisible();
  await expect(page.getByLabel("সংযুক্ত করার বই", { exact: true })).toHaveValue(fixture.source_processing.candidate);
  await expect(page.getByRole("button", { name: "সিদ্ধান্ত সংরক্ষণ করুন", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "বর্তমান যাচাই খুলুন", exact: true })).toBeVisible();
  expect(writes).toBe(1);
});

test("a processor reviews and links a duplicate without metadata permission", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/manage/jobs/${fixture.source_processing.duplicate}/`);
  await expect(page.getByRole("heading", { name: "একই নামে বই পাওয়া গেছে", exact: true })).toBeVisible();
  await page.getByLabel("করণীয় নির্বাচন করুন", { exact: true }).selectOption("link");
  await page.getByLabel("সংযুক্ত করার বই", { exact: true }).selectOption(fixture.source_processing.candidate);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/source-decision-320.png", fullPage: true });
  await page.getByRole("button", { name: "সিদ্ধান্ত সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("সম্পন্ন");
  await expect(page.getByRole("link", { name: "বইয়ের তথ্য দেখুন →", exact: true })).toHaveCount(0);
  const response = await page.request.get(`/api/v1/manage/jobs/${fixture.source_processing.duplicate}/`);
  expect((await response.json()).book.id).toBe(fixture.source_processing.candidate);
});

test("failed source exports resume the linked draft from its detail page", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/manage/sources/${fixture.source_processing.failed_source}/`);
  await page.getByRole("link", { name: "সর্বশেষ কাজ ও করণীয় দেখুন →", exact: true }).click();
  await expect(page.getByLabel("করণীয় নির্বাচন করুন", { exact: true })).toHaveValue("resume_preparation");
  await expect(page.getByLabel("করণীয় নির্বাচন করুন", { exact: true }).locator('option[value="retry"]')).toHaveCount(0);
  await page.screenshot({ path: "test-artifacts/foundation/source-recovery-390.png", fullPage: true });
  await page.getByRole("button", { name: "সিদ্ধান্ত সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toContainText("অপেক্ষমাণ");
  const result = await (await page.request.get(`/api/v1/manage/jobs/${fixture.source_processing.failed}/`)).json();
  expect(result.book.id).toBe(fixture.source_processing.draft);
});

test("bulk source outcomes preserve only unsuccessful selections", async ({ page }) => {
  await useAccount(page, "source_processor"); await page.goto(`/manage/sources/?q=${fixture.sources.query}`);
  const enabled = page.locator('input[type="checkbox"]:not([disabled])');
  const first = enabled.nth(0), second = enabled.nth(1);
  await first.check(); await second.check();
  const titles = await page.locator(".job-card").filter({ has: page.locator('input[type="checkbox"]:checked') }).locator("h2").allTextContents();
  const pending = await page.request.get(`/api/v1/manage/sources/?q=${fixture.sources.query}`);
  const sources = (await pending.json()).entries;
  const entry = sources.find((source) => source.title === titles[0]);
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const separate = await page.request.post(`/api/v1/manage/sources/${entry.id}/process/`, { data: { operation_id: crypto.randomUUID(), expected_updated_at: entry.updated_at }, headers: { "X-CSRFToken": session.csrf_token } });
  expect(separate.status()).toBe(202);
  await page.getByRole("button", { name: "নির্বাচিত উৎস প্রক্রিয়ার অনুরোধ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "ব্যর্থ উৎসগুলো নির্বাচিত আছে" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: `${titles[0]} নির্বাচন করুন`, exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: `${titles[1]} নির্বাচন করুন`, exact: true })).not.toBeChecked();
  await expect(page.getByRole("link", { name: "সংরক্ষিত কাজ দেখুন →", exact: true })).toHaveCount(1);
});
