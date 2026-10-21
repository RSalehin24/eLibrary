import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test("book totals show lifecycle counts without a manual-review counter in either language", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await useAccount(page, "administrator");
  const { books } = await (await page.request.get("/api/v1/manage/overview/")).json();
  expect(books.editorial_pending).toBe(0);
  expect(books.total).toBe(books.draft + books.processing + books.ready + books.published + books.archived);
  await page.goto("/manage/overview/");
  for (const [language, title, labels] of [
    ["bn", "বইয়ের তালিকা", ["মোট", "প্রক্রিয়াধীন", "প্রকাশিত", "আর্কাইভে", "প্রকাশের অপেক্ষায়"]],
    ["en", "Books", ["Total", "Processing", "Published", "Archived", "Awaiting Publication"]],
  ]) {
    await setLanguage(page, language);
    const card = page.locator("section.account-section").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
    for (const [index, key] of ["total", "processing", "published", "archived", "awaiting"].entries()) {
      const row = card.locator(".book-facts > div").filter({ has: page.locator("dt", { hasText: new RegExp(`^${labels[index]}$`) }) });
      const count = key === "awaiting" ? books.draft + books.ready : books[key];
      if (key === "awaiting" && count === 0) await expect(row).toHaveCount(0);
      else await expect(row.locator("dd")).toHaveText(new Intl.NumberFormat(language, { numberingSystem: language === "bn" ? "beng" : "latn" }).format(count));
    }
    await expect(page.getByText(/পর্যালোচনা বাকি|সম্পাদকীয় পর্যালোচনা|Awaiting Review|Drafts|^খসড়া$/)).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.goto("/manage/automations/new/");
  await expect(page.getByText("Books are checked and published automatically.", { exact: true })).toBeVisible();
  await setLanguage(page, "bn");
  await expect(page.getByText("স্বয়ংক্রিয়ভাবে যাচাই ও প্রকাশ করা হবে।", { exact: true })).toBeVisible();
  await expect(page.getByText(/সম্পাদকের পর্যালোচনা প্রয়োজন|Books require review/)).toHaveCount(0);
});

test("overview is private and shows each administrator's authorized sections", async ({ page }) => {
  await useAccount(page, "reader"); expect((await page.request.get("/manage/")).status()).toBe(404);
  expect((await page.request.get("/api/v1/manage/overview/")).status()).toBe(403);
  await useAccount(page, "editor"); await page.goto("/manage/overview/");
  await expect(page.getByRole("heading", { name: "বইয়ের তালিকা", exact: true })).toBeVisible();
  for (const name of ["ওয়েবসাইটের বই", "ব্যবহারকারী", "বই তৈরির কাজ", "আমন্ত্রণের ইমেইল"]) await expect(page.getByRole("heading", { name, exact: true })).toHaveCount(0);
  await useAccount(page, "source_processor"); await page.goto("/manage/overview/");
  await expect(page.getByRole("heading", { name: "ওয়েবসাইটের বই", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "বই তৈরির কাজ", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "আমন্ত্রণের ইমেইল", exact: true })).toHaveCount(0);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
});

test("phone overview provides actionable processing and mail failures without crossing permissions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await useAccount(page, "administrator"); await page.goto("/manage/overview/");
  const work = await (await page.request.get("/api/v1/manage/overview/work/")).json();
  const failed = work.processing.issues.find((issue) => issue.state === "failed");
  expect(failed).toBeTruthy();
  const issue = page.locator(`a[href="/manage/jobs/${failed.id}/"]`);
  await expect(issue).toBeVisible(); await issue.click();
  await expect(page.locator(".status-label")).toHaveText("ব্যর্থ");
  await useAccount(page, "access_manager"); await page.goto("/manage/overview/");
  await expect(page.getByRole("heading", { name: "আমন্ত্রণের ইমেইল", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "বই তৈরির কাজ", exact: true })).toHaveCount(0);
  const mailWork = await (await page.request.get("/api/v1/manage/overview/work/")).json();
  const uncertain = mailWork.account_mail.issues.find((issue) => issue.error_code === "mail_acceptance_unknown");
  expect(uncertain).toBeTruthy();
  const mail = page.locator(`a[href="/manage/users-access/mail/${uncertain.id}/"]`); await expect(mail).toBeVisible();
  await page.screenshot({ path: "test-artifacts/foundation/overview-390.png", fullPage: true }); await mail.click();
  await expect(page.locator(".status-label")).toHaveText("যাচাই প্রয়োজন");
  await expect(page.getByText("স্বয়ংক্রিয়ভাবে আবার পাঠানো হবে না", { exact: false })).toBeVisible();
});

test("overview polling refreshes work without repeating catalog summary reads", async ({ page }) => {
  await useAccount(page, "administrator"); const reads = { work: 0, summary: 0 };
  page.on("request", (request) => { const path = new URL(request.url()).pathname;
    if (path === "/api/v1/manage/overview/work/") reads.work += 1;
    if (path === "/api/v1/manage/overview/") reads.summary += 1;
  });
  await page.goto("/manage/overview/"); await expect.poll(() => reads.work).toBeGreaterThan(0);
  expect(reads.summary).toBe(0);
  await page.getByRole("button", { name: "হালনাগাদ করুন", exact: true }).click();
  await expect.poll(() => reads.summary).toBe(1);
});

test("overview summary renders without JavaScript at 320 pixels", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, javaScriptEnabled: false, viewport: { width: 320, height: 800 } });
  const page = await context.newPage(); await useAccount(page, "editor");
  await page.goto("/manage/overview/"); await expect(page.getByRole("heading", { name: "বইয়ের তালিকা", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "বই দেখুন", exact: true })).toBeVisible(); await context.close();
});
