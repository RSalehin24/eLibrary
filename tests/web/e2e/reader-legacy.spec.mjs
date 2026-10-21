import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

async function openReader(page) {
  await useAccount(page, "legacy_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.legacy_reading.book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(response.status()).toBe(200);
  const session = await response.json();
  await page.route("**/api/v1/reading/sessions/*/progress/", route => route.fulfill({ json: route.request().postDataJSON() }));
  await page.goto(`/reader/${session.id}/`);
  await setLanguage(page, "en");
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
  return session;
}

test("original relative reading locations and nested contents open the actual section", async ({ page }) => {
  const session = await openReader(page);
  expect(session.navigation.some(entry => entry.depth === 1 && entry.fragment === "paragraph-40")).toBe(true);
  const frame = page.frameLocator(".reader-frame");
  await expect(frame.getByRole("heading", { name: "দ্বিতীয় অধ্যায়", exact: true })).toBeVisible();
  await expect.poll(() => frame.locator("#paragraph-40").evaluate(element => Math.abs(element.getBoundingClientRect().top))).toBeLessThan(100);
  await page.getByRole("button", { name: "Contents", exact: true }).click();
  const dialog = page.getByRole("dialog"), child = dialog.getByRole("button", { name: "প্রথম পর্বের অংশ", exact: true });
  const toggle = dialog.getByRole("button", { name: /^(?:Collapse|Expand) contents: প্রথম অধ্যায়$/ });
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await toggle.focus(); await page.keyboard.press("Enter");
  await expect(child).not.toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("Space");
  await expect(child).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "প্রথম পর্বের অংশ", exact: true }).click();
  await expect(frame.getByRole("heading", { name: "প্রথম অধ্যায়", exact: true })).toBeVisible();
  await expect.poll(() => frame.locator("#paragraph-40").evaluate(element => Math.abs(element.getBoundingClientRect().top))).toBeLessThan(100);
  await page.getByRole("button", { name: "Contents", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Collapse contents: প্রথম অধ্যায়", exact: true })).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await page.screenshot({ path: `test-artifacts/foundation/reader-legacy-section-${test.info().project.name}.png` });
});

test("original CFI bookmarks and highlights retain UTF-16 positions and reject mismatched editions", async ({ page }) => {
  await openReader(page);
  const frame = page.frameLocator(".reader-frame");
  await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "প্রথম অধ্যায়", exact: true }).click();
  await expect(frame.locator("mark[data-library-highlight]")).toHaveText(fixture.legacy_reading.quote);
  await expect.poll(() => frame.locator("#paragraph-40").evaluate(element => element.getBoundingClientRect().top < innerHeight && element.getBoundingClientRect().bottom > 0)).toBe(true);
  await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
  await page.getByRole("dialog").getByRole("button").filter({ hasText: fixture.legacy_reading.quote }).click();
  await expect.poll(() => frame.locator("body").evaluate(() => document.getSelection()?.toString())).toBe(fixture.legacy_reading.quote);
  await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
  await page.getByRole("dialog").getByRole("button").filter({ hasText: "Text from a different edition" }).click();
  await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
  await expect(frame.locator("mark[data-library-highlight]")).toHaveText(fixture.legacy_reading.quote);
  await setLanguage(page, "bn");
  await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("আপনার নোট সংরক্ষিত আছে");
});

async function gesture(page, kind) {
  await page.frameLocator(".reader-frame").locator("body").evaluate((body, kind) => {
    const doc = body.ownerDocument;
    const send = (type, touches, changedTouches = touches) => {
      const event = new Event(type, { bubbles: true, cancelable: true });
      Object.defineProperties(event, { touches: { value: touches }, changedTouches: { value: changedTouches } });
      body.dispatchEvent(event);
    };
    const point = x => ({ clientX: x, clientY: 10 });
    doc.getSelection()?.removeAllRanges();
    if (kind === "pinch") { send("touchstart", [point(0), point(100)]); send("touchmove", [point(-30), point(130)]); send("touchend", [], [point(-30), point(130)]); }
    else if (kind === "theme") { send("touchstart", [point(0), point(100)]); send("touchend", [], [point(0), point(100)]); }
    else for (let tap = 0; tap < 2; tap++) { send("touchstart", [point(10)]); send("touchend", [], [point(10)]); }
  }, kind);
}

test("reader gestures resize text, change themes and enter immersive reading without intercepting selections", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(document, "fullscreenEnabled", { configurable: true, value: false }));
  await openReader(page);
  const frame = page.frameLocator(".reader-frame");
  await gesture(page, "theme"); await expect(frame.locator("body")).toHaveCSS("background-color", "rgb(241, 231, 209)");
  await gesture(page, "pinch"); await expect(frame.locator("body")).toHaveCSS("font-size", "24px");
  await gesture(page, "immersive"); await expect(page.locator(".reader-workspace")).toHaveClass(/reader-focus-mode/);
  await expect(page.locator(".reader-workspace button:visible")).toHaveCount(0);
  await page.screenshot({ path: `test-artifacts/foundation/reader-legacy-immersive-${test.info().project.name}.png` });
  await gesture(page, "immersive"); await expect(page.getByRole("button", { name: "Contents", exact: true })).toBeVisible();
  const selected = await frame.locator("body").evaluate(body => { const text = body.querySelector("p").firstChild, range = body.ownerDocument.createRange(); range.setStart(text, 0); range.setEnd(text, text.textContent.indexOf(" ")); const selection = body.ownerDocument.getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); });
  expect(selected.length).toBeGreaterThan(0);
  await frame.locator("body").evaluate(body => body.dispatchEvent(new Event("dblclick", { bubbles: true, cancelable: true })));
  await expect(page.getByRole("button", { name: "Contents", exact: true })).toBeVisible();
  await expect.poll(() => frame.locator("body").evaluate(() => document.getSelection()?.toString())).toBe(selected);
});

test("an older prepared book remains readable while its administrator queues updated reader files", async ({ page }, info) => {
  await useAccount(page, "administrator");
  const book = fixture.reader_update_books[info.project.name];
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(launched.status()).toBe(200);
  const session = await launched.json();
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await setLanguage(page, "en");
  await expect(page.getByRole("link", { name: "Continue Reading", exact: true })).toHaveAttribute("href", `/reader/${session.id}/`);
  const accepted = page.waitForResponse(response => response.url().endsWith("/prepare/") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Update Reader Files", exact: true }).click();
  expect((await accepted).status()).toBe(202);
  await expect(page.locator(".asset-file").getByRole("link", { name: "View Preparation Job", exact: true })).toBeVisible();
  expect((await page.request.get(`/api/v1/reading/sessions/${session.id}/`)).status()).toBe(200);
  await page.getByRole("link", { name: "Continue Reading", exact: true }).click();
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
});

test("an original element CFI scrolls to its exact image without rewriting the saved legacy record", async ({ page }) => {
  await useAccount(page, "legacy_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.legacy_reading.book.slug)}/launch/`, { headers });
  const session = await launched.json();
  const chapter = session.chapters[0];
  const resourceURL = session.resource_base + chapter.path;
  const response = await page.request.get(resourceURL);
  const source = (await response.text()).replace(/<\/body\s*>/i, '<img id="legacy-cfi-image" width="200" height="200" alt="Legacy image" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=" /></body>');
  const localPath = await page.evaluate(source => {
    const doc = new DOMParser().parseFromString(source, "application/xhtml+xml");
    const target = doc.getElementById("legacy-cfi-image");
    const steps = [];
    for (let element = target; element && element !== doc.documentElement; element = element.parentElement) steps.unshift((Array.from(element.parentElement.children).indexOf(element) + 1) * 2);
    return steps.map(step => `/${step}`).join("") + "[legacy-cfi-image]";
  }, source);
  const last_location = `epubcfi(/${chapter.spine_step ?? 6}/${((chapter.spine_index ?? 0) + 1) * 2}!${localPath})`;
  const progressURL = `/api/v1/reading/sessions/${session.id}/progress/`;
  expect((await page.request.put(progressURL, { headers, data: { last_location, progress_percent: 0 } })).status()).toBe(200);
  try {
    await page.route(`**${resourceURL}`, route => route.fulfill({ body: source, contentType: "application/xhtml+xml" }));
    await page.route("**/api/v1/reading/sessions/*/progress/", route => route.fulfill({ json: route.request().postDataJSON() }));
    await page.goto(`/reader/${session.id}/`);
    await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
    await expect.poll(() => page.frameLocator(".reader-frame").locator("#legacy-cfi-image").evaluate(element => element.getBoundingClientRect().top < innerHeight && element.getBoundingClientRect().bottom > 0)).toBe(true);
    const persisted = await (await page.request.get(`/api/v1/reading/sessions/${session.id}/`)).json();
    expect(persisted.reading_progress.last_location).toBe(last_location);
  } finally {
    expect((await page.request.put(progressURL, { headers, data: session.reading_progress })).status()).toBe(200);
  }
});

test("missing original section fragments report that the stored place could not be restored", async ({ page }) => {
  const session = await openReader(page);
  const frame = page.frameLocator(".reader-frame");
  await frame.locator("body").evaluate((body, target) => {
    const link = body.ownerDocument.createElement("a");
    link.href = target; link.textContent = "Missing legacy section"; body.prepend(link);
  }, session.resource_base + session.chapters[0].path + "#missing-legacy-section");
  await frame.getByRole("link", { name: "Missing legacy section", exact: true }).click();
  await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
});
