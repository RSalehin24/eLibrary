import { readFile } from "node:fs/promises";
import { test, expect, fixture, useAccount, artifactPath, setLanguage } from "./fixtures.mjs";

test("My Books prioritizes results while keeping filters and exports usable in both languages", async ({ page }) => {
  await useAccount(page, "personal_reader");
  for (const { width, height, language } of [
    { width: 1365, height: 900, language: "English" }, { width: 1365, height: 900, language: "বাংলা" },
    { width: 390, height: 844, language: "English" }, { width: 390, height: 844, language: "বাংলা" },
  ]) {
    await page.setViewportSize({ width, height }); await page.goto("/my-books/?view=granted");
    await setLanguage(page, language === "English" ? "en" : "bn");
    const book = page.locator(".book-card").filter({ hasText: fixture.personal.private.title });
    await expect(book).toBeVisible();
    const bounds = await book.boundingBox(), exports = await page.locator(".catalog-export-controls").boundingBox();
    expect(bounds.y).toBeLessThan(width > 1000 ? height - 100 : height * 1.2);
    expect(exports.y).toBeGreaterThan(bounds.y + bounds.height);
    await expect(page.locator(".catalog-filters-form").getByRole("link")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: artifactPath(`library-density-${test.info().project.name}-${width}-${language === "English" ? "en" : "bn"}.png`), fullPage: true });
  }
  const form = page.locator(".catalog-filters-form");
  await form.getByRole("searchbox").fill(fixture.personal.private.title);
  await form.getByRole("link", { name: "ফিল্টার সরান", exact: true }).click();
  expect(new URL(page.url()).searchParams.get("view")).toBe("granted");
  await expect(form.getByRole("searchbox")).toHaveValue("");
  await page.locator(".catalog-export-controls summary").click();
  const downloading = page.waitForEvent("download");
  await page.locator(".catalog-export-controls").getByRole("button", { name: "CSV", exact: true }).click();
  const download = await downloading;
  expect(await readFile(await download.path(), "utf8")).toContain(fixture.personal.private.title);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await form.locator("summary").click();
  await expect(form.getByLabel("লেখক বা সহযোগী", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("saved and granted library views do not transfer ownership", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  await page.getByRole("button", { name: "আমার বইয়ে যোগ করুন", exact: true }).click();
  await expect(page.getByRole("button", { name: "আমার বই থেকে সরান", exact: true })).toBeVisible();
  await page.goto("/my-books/"); await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
  const tabs = page.locator(".personal-library-tabs");
  const bounds = await tabs.boundingBox();
  expect(bounds.height).toBeLessThan(page.viewportSize().width >= 1024 ? 120 : page.viewportSize().height / 2);
  for (const link of await tabs.getByRole("link").all()) expect((await link.boundingBox()).height).toBeGreaterThanOrEqual(44);
  await page.goto("/my-books/?view=owned"); await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "অনুমতি পাওয়া বই", exact: true }).click();
  await expect(page.getByRole("heading", { name: fixture.personal.private.title, exact: true })).toBeVisible();
  await page.getByRole("heading", { name: fixture.personal.private.title, exact: true }).getByRole("link").click();
  await expect(page.getByRole("heading", { name: fixture.personal.private.title, exact: true })).toBeVisible();
});

test("ordinary saved books have no type label or physical-reading form on a phone", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await expect(page.getByRole("heading", { name: fixture.personal.paper.title, exact: true })).toBeVisible();
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveCount(0);
  await expect(page.locator("main").getByText("কাগজের বই", { exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: artifactPath("unified-personal-book-320.png"), fullPage: true });
});

test("published book pages link other public editions without draft metadata", async ({ page }) => {
  await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  const section = page.locator("section").filter({ has: page.getByRole("heading", { name: "এই কাজের অন্য সংস্করণ", exact: true }) });
  await expect(section).toContainText(fixture.personal.edition.title);
  await expect(section).not.toContainText("গোপন সংস্করণ");
  await section.getByRole("link", { name: `${fixture.personal.edition.title} · দ্বিতীয় · bn`, exact: true }).click();
  await expect(page.getByRole("heading", { name: fixture.personal.edition.title, exact: true })).toBeVisible();
});

test("book details show the actual last chapter and resume the saved position in both languages", async ({ page }) => {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers });
  expect(launched.status()).toBe(200);
  const session = await launched.json();
  const saved = await page.request.put(`/api/v1/reading/sessions/${session.id}/progress/`, { headers, data: { last_location: "chapter:1:0.4", progress_percent: 70 } });
  expect(saved.status()).toBe(200);
  await page.goto(`/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  const summary = page.getByRole("region", { name: "আপনার পড়া ও নোট", exact: true });
  await expect(summary.getByRole("heading", { name: "যেখানে পড়া থামিয়েছেন", exact: true })).toBeVisible();
  await expect(summary.locator(".book-last-location")).toContainText(session.chapters[1].label);
  await expect(summary.locator(".book-last-location")).toContainText("৪০%");
  await expect(summary.locator(".book-last-location")).not.toContainText("chapter:1:");
  await setLanguage(page, "en");
  const english = page.getByRole("region", { name: "Your reading and notes", exact: true });
  await expect(english.getByRole("heading", { name: "Where you stopped reading", exact: true })).toBeVisible();
  await expect(english.locator(".book-last-location")).toContainText("40%");
  await english.getByRole("link", { name: "Resume where you stopped", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/reader/${session.id}/$`));
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: "দ্বিতীয় অধ্যায়", exact: true })).toBeVisible();
});

test("unknown or mismatched saved-edition locations never show a guessed chapter or raw CFI", async ({ page }) => {
  await useAccount(page, "reading_reader");
  let progressSessionId = "00000000-0000-4000-8000-000000000002";
  await page.route("**/api/v1/reading/books/*/access/", async route => {
    const response = await route.fetch();
    const access = await response.json();
    await route.fulfill({ json: { ...access, active_session_id: "00000000-0000-4000-8000-000000000001", progress_session_id: progressSessionId || undefined, reading_progress: { last_location: "epubcfi(unresolved-private-position)", progress_percent: 70 } } });
  });
  await page.goto(`/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  const summary = page.getByRole("region", { name: "আপনার পড়া ও নোট", exact: true });
  await expect(summary.locator(".book-last-location")).toContainText("পড়ার অবস্থান সংরক্ষিত আছে।");
  await expect(summary.locator(".book-last-location")).not.toContainText("epubcfi");
  await expect(summary.getByRole("link", { name: "যেখানে থেমেছিলেন সেখান থেকে পড়ুন", exact: true })).toHaveCount(0);
  progressSessionId = "";
  await page.reload();
  await expect(summary.locator(".book-last-location")).toContainText("পড়ার অবস্থান সংরক্ষিত আছে।");
  await expect(summary.locator(".book-last-location").getByRole("link")).toHaveCount(0);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("profile image upload is private and can be removed without losing another draft", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.goto("/profile/");
  await page.getByLabel("নাম", { exact: true }).fill("ছবির পাশাপাশি অসম্পূর্ণ নাম");
  await page.getByLabel("নতুন প্রোফাইলের ছবি", { exact: true }).setInputFiles({ name: "avatar.png", mimeType: "image/png", buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=", "base64") });
  await page.getByRole("button", { name: "ছবি সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("img", { name: "আপনার প্রোফাইলের ছবি", exact: true })).toBeVisible();
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("ছবির পাশাপাশি অসম্পূর্ণ নাম");
  const image = await page.getByRole("img", { name: "আপনার প্রোফাইলের ছবি", exact: true }).getAttribute("src");
  expect(image).toContain("/api/v1/auth/profile/image/");
  await page.getByRole("button", { name: "প্রোফাইলের ছবি সরান", exact: true }).click();
  await expect(page.getByRole("img", { name: "আপনার প্রোফাইলের ছবি", exact: true })).toHaveCount(0);
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("ছবির পাশাপাশি অসম্পূর্ণ নাম");
});
