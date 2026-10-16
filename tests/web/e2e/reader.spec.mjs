import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { UpdateProxy } from "../update-proxy.mjs";

test.use({ serviceWorkers: "allow" });

async function openReader(page, origin = "") {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(response.status()).toBe(200);
  const session = await response.json();
  const resource = await page.request.get(session.resource_base + session.chapters[0].path);
  expect(resource.status()).toBe(200);
  expect(resource.headers()["cache-control"]).toContain("no-store");
  const reset = await page.request.put(`/api/v1/reading/sessions/${session.id}/progress/`, { headers: { "X-CSRFToken": account.csrf_token }, data: { last_location: "chapter:0:0", progress_percent: 0 } });
  expect(reset.status()).toBe(200);
  await page.goto(`${origin}/reader/${session.id}/`);
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: "প্রথম অধ্যায়" })).toBeVisible();
  await expect(page.locator(".reader-frame")).toHaveAttribute("aria-busy", "false");
  return session;
}

test("reader launches from the book page and navigates chapters safely", async ({ page }) => {
  await useAccount(page, "reading_reader");
  await page.goto(`/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  await expect(page.getByRole("link", { name: "EPUB ডাউনলোড" })).toBeVisible();
  await page.getByRole("button", { name: "বই পড়ুন", exact: true }).click();
  await expect(page).toHaveURL(/\/reader\/[0-9a-f-]+\/$/);
  const content = page.frameLocator(".reader-frame");
  await expect(content.getByRole("heading", { name: "প্রথম অধ্যায়" })).toBeVisible();
  expect(await content.locator("body").evaluate(() => window.readerScriptExecuted)).toBeUndefined();
  await page.getByRole("button", { name: "সূচিপত্র", exact: true }).click();
  await page.getByRole("button", { name: "দ্বিতীয় অধ্যায়", exact: true }).click();
  await expect(content.getByRole("heading", { name: "দ্বিতীয় অধ্যায়" })).toBeVisible();
  await content.getByRole("link", { name: "অন্য অধ্যায়ে যান" }).click();
  await expect(content.getByRole("heading", { name: "প্রথম অধ্যায়" })).toBeVisible();
  await expect(page.locator(".reader-pagination")).toContainText("প্রথম অধ্যায়");
  await page.getByRole("button", { name: "পড়ার সেটিংস" }).click();
  await page.getByLabel("পাতার রং").selectOption("dark");
  await page.keyboard.press("Escape");
  await expect(content.locator("body")).toHaveCSS("background-color", "rgb(24, 34, 30)");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
});

test("reader exposes failed progress writes and retries the latest position", async ({ page }) => {
  const proxy = new UpdateProxy(); await proxy.start();
  try {
    const session = await openReader(page, proxy.origin); proxy.failProgress = true;
    const failedSave = page.waitForResponse((response) => response.request().method() === "PUT" && response.url().endsWith("/progress/") && response.status() === 503);
    const content = page.frameLocator(".reader-frame").locator("body");
    await content.evaluate(() => { const root = document.scrollingElement; root.scrollTop = (root.scrollHeight - root.clientHeight) / 2; });
    await failedSave;
    await expect(page.locator(".reader-save-status [role=alert]")).toContainText("পড়ার অবস্থান সংরক্ষণ হয়নি");
    await content.evaluate(() => { const root = document.scrollingElement; root.scrollTop = (root.scrollHeight - root.clientHeight) * 0.55; });
    await expect(page.locator(".reader-toolbar")).toContainText(/2[78]%/);
    await expect(page.getByRole("button", { name: "আবার সংরক্ষণ করুন" })).toBeVisible();
    proxy.failProgress = false;
    await page.getByRole("button", { name: "আবার সংরক্ষণ করুন" }).click();
    await expect(page.getByText("পড়ার অবস্থান সংরক্ষিত", { exact: true })).toBeVisible();
    const persisted = await (await page.request.get(`/api/v1/reading/sessions/${session.id}/`)).json();
    expect(persisted.reading_progress.progress_percent).toBeGreaterThan(20);
    expect(persisted.reading_progress.progress_percent).toBeLessThan(30);
  } finally { await proxy.stop(); }
});

test("authored reader content cannot fetch authenticated routes outside its resources", async ({ page }) => {
  const completed = [];
  page.on("response", (response) => { if (response.url().includes("reader-network-canary")) completed.push(response.status()); });
  const session = await openReader(page);
  expect(completed).toEqual([]);
  const canary = page.frameLocator(".reader-frame").locator('img[src*="reader-network-canary"]');
  await expect(canary).toHaveJSProperty("complete", true);
  await expect(canary).toHaveJSProperty("naturalWidth", 0);
  const resource = await page.request.get(session.resource_base + session.chapters[0].path);
  expect(resource.headers()["content-security-policy"]).toContain(`img-src ${new URL(session.resource_base, page.url()).href}`);
  expect(resource.headers()["content-security-policy"]).not.toContain("img-src 'self'");
  expect(completed).toEqual([]);
});

test("reader saves bookmarks, highlights, and private notes with stale-edit protection", async ({ page }) => {
  await openReader(page);
  const body = page.frameLocator(".reader-frame").locator("body");
  await body.evaluate(() => { const root = document.scrollingElement; root.scrollTop = (root.scrollHeight - root.clientHeight) * .25; });
  await page.getByRole("button", { name: "এখানে বুকমার্ক রাখুন" }).click();
  await expect(page.getByText("বুকমার্ক সংরক্ষিত", { exact: true })).toBeVisible();
  await body.evaluate(() => {
    const walker = document.createTreeWalker(document.getElementById("paragraph-12"), NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node && node.length < 45) node = walker.nextNode();
    const range = document.createRange(); range.setStart(node, 0); range.setEnd(node, 45);
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    document.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });
  await page.getByRole("button", { name: "নির্বাচিত লেখায় দাগ দিন" }).click();
  await page.getByLabel("আপনার নোট", { exact: true }).fill("এটি নিজের সংরক্ষিত পাঠের কথা।");
  await page.getByLabel("দাগের রং").selectOption("green");
  const createdResponse = page.waitForResponse((response) => response.url().endsWith("/highlights/") && response.request().method() === "POST");
  await page.getByRole("button", { name: "দাগ ও নোট সংরক্ষণ করুন" }).click();
  const created = await (await createdResponse).json();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(body.locator(`mark[data-library-highlight="${created.id}"]`)).toHaveAttribute("data-color", "green");
  await page.reload();
  await expect(body.locator(`mark[data-library-highlight="${created.id}"]`)).toBeVisible();
  await page.getByRole("button", { name: "বুকমার্ক ও দাগ" }).click();
  await expect(page.getByRole("dialog")).toContainText(created.text);
  await page.keyboard.press("Escape");
  await page.getByRole("link", { name: "নিজের সব নোট →" }).click();
  await expect(page).toHaveURL(/\/notes\/$/);
  await page.locator(`[data-annotation-id="${created.id}"]`).click();
  await page.getByLabel("আপনার নোট", { exact: true }).fill("এই অসম্পূর্ণ লেখাটি হারানো যাবে না।");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const path = `/api/v1/me/highlights/${created.id}/`;
  const concurrent = await page.request.patch(path, { headers: { "X-CSRFToken": account.csrf_token }, data: { expected_updated_at: created.updated_at, note: "অন্য জানালার নতুন কথা।" } });
  expect(concurrent.status()).toBe(200);
  await page.getByRole("button", { name: "নোট সংরক্ষণ করুন" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("নোটটি অন্য জায়গায় বদলেছে");
  await expect(page.getByLabel("আপনার নোট", { exact: true })).toHaveValue("এই অসম্পূর্ণ লেখাটি হারানো যাবে না।");
  await page.getByRole("button", { name: "বন্ধ করুন", exact: true }).click();
  await page.reload();
  await page.locator(`[data-annotation-id="${created.id}"]`).click();
  await page.getByLabel("আপনার নোট", { exact: true }).fill("নিজের পরের কথা।");
  await page.getByRole("button", { name: "নোট সংরক্ষণ করুন" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.locator(`[data-annotation-id="${created.id}"]`).click();
  await page.getByRole("button", { name: "মুছে ফেলুন", exact: true }).click();
  await page.getByRole("button", { name: "হ্যাঁ, মুছে ফেলুন", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect((await page.request.get(path)).status()).toBe(404);
});

test("reader preserves position across resizing and remains usable at 320 pixels", async ({ page }) => {
  await openReader(page);
  const body = page.frameLocator(".reader-frame").locator("body");
  await body.evaluate(() => { const root = document.scrollingElement; root.scrollTop = (root.scrollHeight - root.clientHeight) * .45; });
  await expect(page.getByText(/2[23]% পড়া হয়েছে/)).toBeVisible();
  for (const width of [320, 375, 390, 768, 820, 1024, 1366, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const fraction = () => body.evaluate(() => { const root = document.scrollingElement; return root.scrollTop / (root.scrollHeight - root.clientHeight); });
    await expect.poll(fraction).toBeGreaterThan(.4); await expect.poll(fraction).toBeLessThan(.5);
    const button = await page.getByRole("button", { name: "সূচিপত্র", exact: true }).boundingBox();
    expect(button.width).toBeGreaterThanOrEqual(44); expect(button.height).toBeGreaterThanOrEqual(44);
    if ([390, 1366].includes(width)) await page.screenshot({ path: `test-artifacts/foundation/reader-${width}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 844, height: 390 });
  await page.getByRole("button", { name: "সূচিপত্র", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "সূচিপত্র", exact: true })).toBeFocused();
});
