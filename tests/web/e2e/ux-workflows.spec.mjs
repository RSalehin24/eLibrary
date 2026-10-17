import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

async function linkedSource(page) {
  if (fixture.sources?.linked?.id) {
    const detail = await page.request.get(`/api/v1/manage/sources/${fixture.sources.linked.id}/`);
    expect(detail.status()).toBe(200);
    return detail.json();
  }
  const response = await page.request.get("/api/v1/manage/sources/?status=linked");
  expect(response.status()).toBe(200);
  const entries = (await response.json()).entries;
  const entry = entries.find(source => source.book?.slug === "দেবদাস") ?? entries.find(source => source.book && source.can_edit_book && !source.book.deleted_at);
  expect(entry).toBeTruthy();
  const detail = await page.request.get(`/api/v1/manage/sources/${entry.id}/`);
  expect(detail.status()).toBe(200);
  return detail.json();
}

test("books and primary actions fit the first screen in both languages", async ({ page }) => {
  await useAccount(page, "administrator");
  for (const [width, height] of [[1365, 900], [390, 844]]) {
    await page.setViewportSize({ width, height }); await page.goto("/manage/sources/");
    for (const language of ["English", "বাংলা"]) {
      await page.getByRole("button", { name: language, exact: true }).click();
      const first = page.locator(".source-row").first(); await expect(first).toBeVisible();
      const box = await first.boundingBox(); expect(box.y).toBeLessThan(height - 30);
      for (const action of await page.locator(".admin-main-action").all()) {
        const bounds = await action.boundingBox(); expect(bounds.y + bounds.height).toBeLessThan(height); expect(bounds.height).toBeGreaterThanOrEqual(44);
      }
      if (width > 1200) {
        for (const [index, selector] of [[0, ".source-sync"], [1, ".process-all"], [2, ".source-scheduling"]]) {
          const action = await page.locator(".admin-main-action").nth(index).boundingBox();
          const information = await page.locator(selector).boundingBox();
          expect(Math.abs(action.x - information.x)).toBeLessThan(2);
        }
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await expect(page.locator(".admin-workflow-nav")).toHaveCount(0);
    }
  }
});

test("a completed source exposes actual EPUB and HTML files and direct editorial actions", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  await page.goto(`/manage/sources/${entry.id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: entry.book.title, exact: true })).toBeVisible();
  for (const format of ["EPUB", "HTML"]) {
    const download = page.getByRole("link", { name: `Download ${format}`, exact: true });
    await expect(download).toBeVisible();
    const response = await page.request.get(await download.getAttribute("href"));
    expect(response.status()).toBe(200); expect(response.headers()["content-disposition"]).toContain("attachment");
    expect(response.headers()["cache-control"]).toBe("private, no-store");
    expect(response.headers()["content-type"]).toContain(format === "EPUB" ? "application/epub+zip" : "text/html");
    const content = await response.body(); expect(content.length).toBeGreaterThan(100);
    if (format === "EPUB") expect(content.subarray(0, 2).toString()).toBe("PK");
  }
  await expect(page.getByRole("button", { name: "Prepare for Reading", exact: true })).toHaveCount(0);
  if (entry.content_summary?.check_completeness) await expect(page.locator(".source-content-summary")).toContainText("Only a short text");
  await page.getByRole("link", { name: "Edit & Publish", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: entry.book.title, exact: true })).toBeVisible();
  await expect(page.locator(".editor-toolbar").getByRole("button", { name: "Save Changes", exact: true })).toBeVisible();
  await expect(page.locator(".editor-toolbar").getByRole("button", { name: "Publish", exact: true })).toBeVisible();
});

test("Bengali source dates contain no English day periods, zone labels or digits", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  await page.goto(`/manage/sources/${entry.id}/`);
  const date = page.locator(".source-provenance .muted");
  await expect(date).toContainText("ঢাকা"); expect(await date.innerText()).not.toMatch(/[A-Za-z0-9]/);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(date).toContainText("Dhaka"); expect(await date.innerText()).not.toMatch(/[\u0980-\u09ff]/);
  await expect(date).toContainText(/\d{1,2}:\d{2} [AP]M/);
});

test("HTML opens actual book text in a separate tab and reading opens the prepared book", async ({ page, context }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  await page.goto(`/manage/sources/${entry.id}/`);
  for (const language of ["English", "বাংলা"]) {
    await page.getByRole("button", { name: language, exact: true }).click();
    const html = page.getByRole("link", { name: language === "English" ? "Open HTML (New Tab)" : "HTML খুলুন (নতুন ট্যাব)", exact: true });
    await expect(html).toBeVisible(); await expect(html).toHaveAttribute("target", "_blank");
    const response = await page.request.get(await html.getAttribute("href"));
    expect(response.status()).toBe(200); expect(response.headers()["content-disposition"]).toContain("inline");
    const opened = context.waitForEvent("page"); await html.click(); const preview = await opened;
    await expect(preview.locator("body")).toContainText(entry.book.title);
    const expectedCharacters = Math.floor((entry.content_summary?.body_character_count ?? 0) * 0.8);
    expect((await preview.locator("body").innerText()).length).toBeGreaterThan(Math.max(1, expectedCharacters));
    expect(preview.url()).toContain("/html/"); expect(await preview.evaluate(() => window.opener === null)).toBe(true);
    await expect(page).toHaveURL(new RegExp(`/manage/sources/${entry.id}/$`)); await preview.close();
  }
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.route("**/api/v1/reading/sessions/*/progress/", route => route.fulfill({ json: route.request().postDataJSON() }));
  const read = page.locator(".book-reading-actions").getByRole("button", { name: "Read Book", exact: true }).or(page.locator(".book-reading-actions").getByRole("link", { name: "Continue Reading", exact: true }));
  await expect(read).toBeVisible(); await read.click();
  await expect(page).toHaveURL(/\/reader\/[0-9a-f-]+\/$/);
  await expect(page.getByRole("heading", { level: 1, name: entry.book.title, exact: true })).toBeVisible();
  await expect(page.frameLocator(".reader-frame").locator("body")).not.toBeEmpty();
  await page.getByRole("button", { name: "Contents", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await page.getByRole("dialog").getByRole("button").count()).toBeGreaterThan(1);
  await page.getByRole("dialog").locator(".reader-chapter").last().click();
  await expect.poll(async () => (await page.frameLocator(".reader-frame").locator("body").innerText()).length).toBeGreaterThan(Math.min(entry.content_summary?.body_character_count ?? 1, 200));
});

test("the editor exposes reading actions, and denied access offers no preview or read button", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  await page.goto(`/manage/books/${encodeURIComponent(entry.book.slug)}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("link", { name: "Open HTML (New Tab)", exact: true })).toBeVisible();
  await expect(page.locator(".book-reading-actions")).toContainText(/Read Book|Continue Reading/);
  await page.route("**/api/v1/reading/books/*/access/", route => route.fulfill({ json: { can_read: false, can_download: false, can_send_kindle: false, prepared: true, active_session_id: null, html_url: null } }));
  await page.locator(".book-files").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".book-reading-actions")).toContainText("You do not currently have access");
  await expect(page.getByRole("link", { name: "Open HTML (New Tab)", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Read Book", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Continue Reading", exact: true })).toHaveCount(0);
});

test("missing files and pending reader preparation have honest states and controls", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  const path = `/api/v1/manage/books/${encodeURIComponent(entry.book.slug)}/assets/`;
  const actual = await (await page.request.get(path)).json();
  let files = actual.map(asset => ({ ...asset, file_available: false, download_url: null, reader_ready: false }));
  await page.route(`**${path}`, route => route.fulfill({ json: files }));
  await page.goto(`/manage/sources/${entry.id}/`); await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("link", { name: "Download EPUB", exact: true })).toHaveCount(0);
  await expect(page.locator(".asset-file-info .field-error").first()).toHaveText("File Missing");
  files = actual.map(asset => ({ ...asset, file_available: true, download_url: null, reader_ready: false, active_preparation_id: asset.id }));
  await page.locator(".book-files").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".book-files")).toContainText("Preparing for Online Reading");
  await expect(page.locator(".book-files")).toContainText("You do not have permission to download this file.");
  await expect(page.getByRole("button", { name: "Prepare for Reading", exact: true })).toHaveCount(0);
});

test("profile sections can be reached directly without clearing other forms", async ({ page }) => {
  await useAccount(page, "administrator"); await page.goto("/profile/");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Keep this unsaved name");
  await page.locator(".account-section-nav").getByRole("link", { name: "Change Password", exact: true }).click();
  await expect(page.getByLabel("Current Password", { exact: true })).toBeInViewport();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Keep this unsaved name");
});

test("prepared books display their actual covers and a Kindle action in both managed views", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  for (const path of [`/manage/sources/${entry.id}/`, `/manage/books/${encodeURIComponent(entry.book.slug)}/`]) {
    await page.goto(path);
    const image = page.locator(".source-book-overview img");
    await expect(image).toBeVisible(); await expect.poll(() => image.evaluate(element => element.naturalWidth)).toBeGreaterThan(0);
    const response = await page.request.get(await image.getAttribute("src"));
    expect(response.status()).toBe(200); expect(response.headers()["content-type"]).toMatch(/^image\//);
    for (const language of ["English", "বাংলা"]) {
      await page.getByRole("button", { name: language, exact: true }).click();
      await expect(page.getByRole("link", { name: language === "English" ? "Send to Kindle" : "কিন্ডলে পাঠান", exact: true })).toHaveCount(1);
    }
  }
  await page.getByRole("link", { name: "কিন্ডলে পাঠান", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: entry.book.title, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "যে ঠিকানাগুলোতে পাঠাবেন", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("failed cover loads fall back to the title and unavailable Kindle permission hides the action", async ({ page }) => {
  await useAccount(page, "administrator"); const entry = await linkedSource(page);
  await page.route("**/api/v1/catalog/books/*/cover/**", route => route.fulfill({ status: 404 }));
  await page.route("**/api/v1/reading/books/*/access/", async route => {
    const response = await route.fetch(); await route.fulfill({ json: { ...await response.json(), can_send_kindle: false } });
  });
  await page.goto(`/manage/sources/${entry.id}/`); await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator(".source-book-overview .cover-title")).toHaveText(entry.book.title);
  await expect(page.getByRole("link", { name: "Send to Kindle", exact: true })).toHaveCount(0);
});
