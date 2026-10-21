import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";
import { useIdleDiscoveryOptions } from "./source-console-fixture.mjs";

function fitsViewport() { return document.documentElement.scrollWidth <= innerWidth; }

test("reader home and navigation expose reading tools and keep secondary pages in the account menu", async ({ page }) => {
  await useAccount(page, "personal_reader"); await page.goto("/");
  await expect(page).toHaveURL(/\/my-books\/$/);
  const navigation = page.locator(".site-header .primary-navigation");
  await expect(navigation.getByRole("link")).toHaveCount(4);
  for (const name of ["আমার বই", "বই খুঁজুন", "আমার নোট", "কিন্ডল"]) await expect(navigation.getByRole("link", { name, exact: true }).locator("svg")).toBeVisible();
  await expect(page.locator("main .workspace > .workspace-nav")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  const box = await navigation.boundingBox(); expect(box.y + box.height).toBeLessThanOrEqual(844); expect(box.y).toBeGreaterThan(740);
  await page.locator(".account-menu > summary").click();
  for (const name of ["প্রোফাইল", "কাগজের বই", "নিজের EPUB পড়ুন", "সহায়তা"]) await expect(page.locator(".account-menu").getByRole("link", { name, exact: true })).toBeVisible();
  await page.keyboard.press("Escape"); await expect(page.locator(".account-menu")).not.toHaveAttribute("open");
});

test("default reader lists show content within the approved desktop and phone budgets in both languages", async ({ page }, info) => {
  await useAccount(page, "personal_reader");
  for (const width of [1366, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const language of ["bn", "en"]) {
      for (const pathname of ["/catalog/", "/my-books/"]) {
        await page.goto(pathname); await setLanguage(page, language); await page.evaluate(() => document.fonts.ready);
        const result = page.locator(".continue-reading, .book-grid").first(); await expect(result).toBeVisible();
        expect((await result.boundingBox()).y).toBeLessThanOrEqual(width === 390 ? 390 : 320);
        await expect(page.locator('select[name="record_type"], input[type="date"]')).toHaveCount(0);
        expect(await page.evaluate(fitsViewport)).toBe(true);
        await page.screenshot({ path: info.outputPath(`${pathname.split("/")[1]}-${language}-${width}.png`) });
      }
    }
  }
});

test("book creation exposes its four main actions, eight desktop rows and all six mobile destinations", async ({ page }, info) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 1366, height: 900 });
  await useIdleDiscoveryOptions(page); await page.goto(`/manage/sources/?q=${fixture.sources.query}`); await setLanguage(page, "en");
  const actions = page.locator(".source-creation-actions");
  for (const name of ["Fetch All", "Process All", "Schedule Automation"]) await expect(actions.getByRole("button", { name, exact: true })).toBeVisible();
  await expect(actions.getByRole("link", { name: "Upload EPUB", exact: true })).toHaveAttribute("href", "/manage/books/new/");
  await expect(actions.getByRole("link", { name: "Add paper book", exact: true })).toHaveCount(0);
  const eighth = page.locator(".source-row").nth(7); await expect(eighth).toBeVisible();
  expect((await eighth.boundingBox()).y + (await eighth.boundingBox()).height).toBeLessThanOrEqual(900);
  await page.screenshot({ path: info.outputPath("book-creation-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  const opener = page.getByRole("button", { name: "Open menu", exact: true }); await opener.click();
  const drawer = page.locator(".admin-navigation-drawer"); await expect(drawer).toBeVisible(); await expect(drawer.getByRole("link")).toHaveCount(6);
  for (const link of await drawer.getByRole("link").all()) { const bounds = await link.boundingBox(); expect(bounds.x).toBeGreaterThanOrEqual(0); expect(bounds.x + bounds.width).toBeLessThanOrEqual(390); }
  await page.keyboard.press("Escape"); await expect(drawer).not.toBeVisible(); await expect(opener).toBeFocused();
});

test("schedule and account directories begin with compact actionable search controls", async ({ page }, info) => {
  await useAccount(page, "administrator");
  for (const width of [1366, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const pathname of ["/manage/automations/", "/manage/users-access/"]) {
      await page.goto(pathname); await setLanguage(page, "en");
      const search = page.getByRole("search"); expect((await search.boundingBox()).height).toBeLessThanOrEqual(width === 390 ? 104 : 56);
      expect((await page.locator(".admin-data-table").boundingBox()).y).toBeLessThanOrEqual(width === 390 ? 390 : 320);
      await expect(search.locator('input[type="date"], select[name="record_type"]')).toHaveCount(0);
      expect(await page.evaluate(fitsViewport)).toBe(true);
      await page.screenshot({ path: info.outputPath(`${pathname.split("/")[2]}-${width}.png`) });
    }
  }
});

test("Notes keeps four reachable views, aligned controls and a distinct recoverable error", async ({ page }) => {
  await useAccount(page, "reading_reader"); await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/notes/"); await setLanguage(page, "en");
  const tabs = page.locator(".notes-view-tabs"); await expect(tabs.getByRole("button")).toHaveCount(4);
  for (const button of await tabs.getByRole("button").all()) { const bounds = await button.boundingBox(); expect(bounds.x).toBeGreaterThanOrEqual(0); expect(bounds.x + bounds.width).toBeLessThanOrEqual(390); }
  const search = await page.getByRole("searchbox", { name: "Search notes", exact: true }).boundingBox(), color = await page.getByRole("combobox", { name: "Color", exact: true }).boundingBox();
  expect(Math.abs(search.y - color.y)).toBeLessThanOrEqual(1); expect(Math.abs(search.height - color.height)).toBeLessThanOrEqual(1);
  await page.route("**/api/v1/me/highlights/?*", route => route.fulfill({ status: 503, json: { code: "unavailable", detail: "Unavailable" } }));
  await page.reload(); await expect(page.locator(".personal-notes").getByRole("alert")).toContainText("Could not load notes");
  await expect(page.getByRole("heading", { name: "No notes yet", exact: true })).toHaveCount(0);
  await page.unroute("**/api/v1/me/highlights/?*"); await page.getByRole("button", { name: "Try Again", exact: true }).click();
  await expect(page.locator(".personal-notes").getByRole("alert")).toHaveCount(0);
});

test("schedule preview and reset reflect the actual twelve-hour time that gets saved", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/manage/automations/new/"); await setLanguage(page, "en");
  const name = `Design schedule ${fixture.query}`;
  const fill = async () => {
    await page.getByLabel("Schedule Name", { exact: true }).fill(name);
    await page.getByLabel("First Run Date", { exact: true }).fill("2035-06-15");
    await page.getByLabel("hours", { exact: true }).selectOption("3");
    await page.getByLabel("minutes", { exact: true }).selectOption("45");
    await page.getByLabel("AM or PM", { exact: true }).selectOption("PM");
  };
  await fill(); const preview = page.getByRole("region", { name: "Schedule summary", exact: true });
  await expect(preview).toContainText("3:45"); await expect(preview).toContainText("Dhaka");
  await page.locator("#scheduled-action").selectOption("fetch");
  await expect(preview).toContainText("Only the website catalog will be refreshed.");
  await expect(preview).not.toContainText("published automatically");
  await page.getByRole("button", { name: "Discard Changes", exact: true }).click();
  await expect(page.getByLabel("hours", { exact: true })).toHaveValue("2"); await expect(page.getByLabel("AM or PM", { exact: true })).toHaveValue("AM");
  await expect(preview).toContainText("Choose the first date");
  await fill(); const response = page.waitForResponse(entry => entry.request().method() === "POST" && entry.url().endsWith("/manage/automations/"));
  await page.getByRole("button", { name: "Save Schedule", exact: true }).click();
  const saved = await response; expect(saved.status()).toBe(201);
  const command = saved.request().postDataJSON(); expect(command.first_run_local).toBe("2035-06-15T15:45"); expect(command.time_zone).toBe("Asia/Dhaka"); expect(command.enabled).toBe(false);
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
});

test("a failed catalog search offers recovery without reporting an empty library", async ({ page }) => {
  await page.goto("/catalog/"); await setLanguage(page, "en");
  await page.route("**/api/v1/catalog/books/?*", route => route.fulfill({ status: 503, json: { code: "unavailable", detail: "Unavailable" } }));
  await page.getByRole("searchbox", { name: "Search by title or author", exact: true }).fill(fixture.book.title);
  const error = page.locator("main").getByRole("alert"); await expect(error).toContainText("Could not search");
  await expect(page.getByRole("heading", { name: "No Books Found", exact: true })).toHaveCount(0);
  await page.unroute("**/api/v1/catalog/books/?*"); await error.getByRole("button", { name: "Try Again", exact: true }).click();
  await expect(page.getByRole("heading", { name: fixture.book.title, exact: true })).toBeVisible();
});

test("Continue Reading resumes the saved chapter and removes completed books from the strip", async ({ page }) => {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json(), headers = { "X-CSRFToken": account.csrf_token };
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers });
  expect(launched.status()).toBe(200); const session = await launched.json();
  const progressPath = `/api/v1/reading/sessions/${session.id}/progress/`;
  expect((await page.request.put(progressPath, { headers, data: { last_location: "chapter:1:0.4", progress_percent: 70 } })).status()).toBe(200);
  await page.goto("/my-books/"); await setLanguage(page, "en");
  const strip = page.locator(".continue-reading"); await expect(strip).toContainText(fixture.reading_book.title); await expect(strip).toContainText("70%");
  expect((await page.request.put(progressPath, { headers, data: { last_location: "chapter:1:1", progress_percent: 100 } })).status()).toBe(200);
  await page.reload(); await expect(page.locator(".continue-reading")).toHaveCount(0);
  expect((await page.request.put(progressPath, { headers, data: { last_location: "chapter:1:0.4", progress_percent: 70 } })).status()).toBe(200);
  await page.reload(); await strip.getByRole("link", { name: "Continue Reading", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/reader/${session.id}/$`));
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: session.chapters[1].label, exact:true })).toBeVisible();
});

test("editor destinations retain unsaved metadata and put the main form before file tools", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto(`/manage/books/${encodeURIComponent(fixture.book.slug)}/`);
  const title = page.getByLabel("বইয়ের নাম", { exact: true }), value = `${fixture.book.title} unsaved`;
  await title.fill(value);
  expect(await page.locator("#book-metadata").evaluate(node => !!(node.compareDocumentPosition(document.querySelector("#file-tools")) & Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true);
  for (const label of ["ফাইল", "তথ্যের ইতিহাস", "বইয়ের তথ্য"]) {
    await page.locator(".editorial-workspace>.admin-local-tabs").getByRole("link", { name: label, exact: true }).click();
    await expect(title).toHaveValue(value);
  }
  await expect(page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true })).toBeEnabled();
});
