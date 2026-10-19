import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("saved and granted library views do not transfer ownership", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.goto(`/books/${encodeURIComponent(fixture.book.slug)}/`);
  await page.getByRole("button", { name: "আমার বইয়ে যোগ করুন", exact: true }).click();
  await expect(page.getByRole("button", { name: "আমার বই থেকে সরান", exact: true })).toBeVisible();
  await page.goto("/my-books/"); await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
  await page.goto("/my-books/?view=owned"); await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "অনুমতি পাওয়া বই", exact: true }).click();
  await expect(page.getByRole("heading", { name: fixture.personal.private.title, exact: true })).toBeVisible();
  await page.getByRole("heading", { name: fixture.personal.private.title, exact: true }).getByRole("link").click();
  await expect(page.getByRole("heading", { name: fixture.personal.private.title, exact: true })).toBeVisible();
});

test("paper reading logs persist privately and appear in recent reading on a phone", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`); await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await expect(page.locator("main").getByText("কাগজের বই", { exact: true })).toBeVisible();
  await page.getByLabel("পড়ার অবস্থা", { exact: true }).selectOption("reading");
  await page.getByLabel("বর্তমান পৃষ্ঠা", { exact: true }).fill("25"); await page.getByLabel("মোট পৃষ্ঠা (ঐচ্ছিক)", { exact: true }).fill("100");
  await page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true }).fill("আমার ব্যক্তিগত কাগজের বইয়ের নোট");
  await page.getByRole("button", { name: "পড়ার হিসাব সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পড়ার হিসাব সংরক্ষিত হয়েছে" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/physical-reading-320.png", fullPage: true });
  await page.reload(); await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveValue("আমার ব্যক্তিগত কাগজের বইয়ের নোট");
  await page.goto("/my-books/?view=recent"); await expect(page.getByText("পড়া হয়েছে ২৫%", { exact: true })).toBeVisible();
  await useAccount(page, "reader"); await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`);
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveValue("");
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
  await page.getByRole("button", { name: "English", exact: true }).click();
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
