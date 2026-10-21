import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";
import { setReadingView, increaseTextSize } from "./reader-controls.mjs";

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

function readerAPI() {
  // The reference web proxy already forwards browser requests to this API.
  return process.env.FOUNDATION_READER_API_URL ?? "";
}

async function openPreparedReader(page) {
  await useAccount(page, "reading_reader");
  const apiOrigin = await readerAPI(page);
  const account = await (await page.request.get(`${apiOrigin}/api/v1/auth/session/`)).json();
  const launched = await page.request.post(`${apiOrigin}/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(launched.status()).toBe(200);
  const session = await launched.json();
  const reset = await page.request.put(`${apiOrigin}/api/v1/reading/sessions/${session.id}/progress/`, {
    headers: { "X-CSRFToken": account.csrf_token },
    data: { last_location: "chapter:0:0", progress_percent: 0 },
  });
  expect(reset.status()).toBe(200);
  await page.route("**/api/v1/reading/sessions/*/progress/", route => route.fulfill({ json: route.request().postDataJSON() }));
  await page.goto(`/reader/${session.id}/`);
  return session;
}

test("reader controls translate while book text, chapter titles and reading settings are preserved", async ({ page }) => {
  await openPreparedReader(page);
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: "প্রথম অধ্যায়", exact: true })).toBeVisible();
  await setLanguage(page, "en");
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await expect(page.getByLabel("Page Theme", { exact: true })).toBeVisible();
  await page.getByLabel("Page Theme", { exact: true }).selectOption("sepia");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await setLanguage(page, "bn");
  await page.getByRole("button", { name: "পড়ার সেটিংস", exact: true }).click();
  await expect(page.getByLabel("পাতার রং", { exact: true })).toHaveValue("sepia");
  await page.getByRole("button", { name: "বন্ধ করুন", exact: true }).click();
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: "প্রথম অধ্যায়", exact: true })).toBeVisible();
});

test("generated source chapters use the reader's margins on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openPreparedReader(page);
  const content = page.frameLocator(".reader-frame");
  await content.locator("body").evaluate(body => {
    const wrapper = body.ownerDocument.createElement("div");
    wrapper.style.cssText = 'margin:40px;font-family:"Kalpurush",sans-serif';
    wrapper.append(...body.childNodes); body.append(wrapper);
  });
  await setLanguage(page, "en");
  await increaseTextSize(page);
  const width = await content.locator("#paragraph-1").evaluate(element => element.getBoundingClientRect().width);
  expect(width).toBeGreaterThan(320);
  expect(await content.locator("body").evaluate(body => body.scrollWidth <= innerWidth)).toBe(true);
});

test("reader has real pagination, text resizing, two page views and persistent appearance", async ({ page }) => {
  await openPreparedReader(page);
  await setLanguage(page, "en");
  const content = page.frameLocator(".reader-frame");
  await setReadingView(page, "single");
  await expect(content.locator("html")).toHaveAttribute("data-reader-view", "single");
  await expect.poll(() => content.locator("html").evaluate(root => root.scrollWidth > root.clientWidth)).toBe(true);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect.poll(() => content.locator("html").evaluate(root => root.scrollLeft)).toBeGreaterThan(0);
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } });
  await page.keyboard.press("ArrowLeft");
  await expect.poll(() => content.locator("html").evaluate(root => root.scrollLeft)).toBe(0);
  await increaseTextSize(page);
  await expect(content.locator("body")).toHaveCSS("font-size", "22px");
  await expect(content.locator("p").first()).toHaveCSS("font-size", "22px");
  for (let step = 0; step < 4; step++) await page.getByRole("button", { name: "Decrease Text Size", exact: true }).click();
  await expect(page.getByRole("button", { name: "Decrease Text Size", exact: true })).toBeDisabled();
  await expect(content.locator("body")).toHaveCSS("font-size", "14px");
  for (let step = 0; step < 4; step++) await page.getByRole("button", { name: "Increase Text Size", exact: true }).click();
  await setReadingView(page, "spread");
  await expect(content.locator("html")).toHaveAttribute("data-reader-view", "spread");
  const metrics = await content.locator("body").evaluate(body => ({ column: parseFloat(getComputedStyle(body).columnWidth), width: document.documentElement.clientWidth }));
  expect(Math.abs(metrics.column - (metrics.width >= 900 ? (metrics.width - 96) / 2 : metrics.width - 48))).toBeLessThan(2);
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await page.getByLabel("Page Theme", { exact: true }).selectOption("dark");
  await page.getByLabel("Font", { exact: true }).selectOption("sans");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(content.locator("body")).toHaveCSS("background-color", "rgb(24, 34, 30)");
  await page.reload();
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await expect(page.getByLabel("Reading View", { exact: true })).toHaveValue("spread");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(content.locator("body")).toHaveCSS("font-size", "22px");
  await expect(content.locator("body")).toHaveCSS("background-color", "rgb(24, 34, 30)");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("reader enters and exits fullscreen or the supported focus view without losing the book", async ({ page }) => {
  await openPreparedReader(page); await setLanguage(page, "en");
  const supported = await page.evaluate(() => document.fullscreenEnabled === true && !!Element.prototype.requestFullscreen);
  await page.getByRole("button", { name: supported ? "Fullscreen" : "Focus Mode", exact: true }).click();
  if (supported) await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(true);
  else await expect(page.locator(".reader-workspace")).toHaveClass(/reader-focus-mode/);
  await expect(page.frameLocator(".reader-frame").locator("body")).not.toBeEmpty();
  await expect(page.locator(".reader-toolbar")).not.toBeVisible();
  await expect(page.locator(".reader-workspace button:visible")).toHaveCount(0);
  await expect(page.locator(".reader-header")).not.toBeVisible();
  await expect(page.locator(".reader-page-controls")).not.toBeVisible();
  await expect.poll(async () => (await page.locator(".reader-frame").boundingBox()).height / await page.evaluate(() => innerHeight)).toBeGreaterThan(.98);
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } });
  await page.keyboard.press("Escape");
  await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(false);
  await expect(page.locator(".reader-workspace")).not.toHaveClass(/reader-focus-mode/);
});

test("browsers without native fullscreen retain an immersive keyboard-accessible focus view", async ({ page }) => {
  await page.addInitScript(() => { Object.defineProperty(document, "fullscreenEnabled", { value: false }); });
  await openPreparedReader(page); await setLanguage(page, "en");
  await page.getByRole("button", { name: "Focus Mode", exact: true }).click();
  await expect(page.locator(".reader-workspace")).toHaveClass(/reader-focus-mode/);
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } }); await page.keyboard.press("Escape");
  await expect(page.locator(".reader-workspace")).not.toHaveClass(/reader-focus-mode/);
  await page.keyboard.press("f");
  await expect(page.locator(".reader-workspace")).toHaveClass(/reader-focus-mode/);
});

test("original theme and text shortcuts work inside chapters and leave search editing alone", async ({ page }) => {
  await openPreparedReader(page); await setLanguage(page, "en");
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } });
  await page.keyboard.press("Control+2");
  const body = page.frameLocator(".reader-frame").locator("body");
  await expect(body).toHaveCSS("background-color", "rgb(241, 231, 209)");
  await page.keyboard.press("Control+=");
  await expect(body).toHaveCSS("font-size", "22px");
  await page.keyboard.press("Control+-");
  await expect(body).toHaveCSS("font-size", "20px");
  await page.getByRole("button", { name: "Search Book", exact: true }).click();
  const search = page.getByLabel("Word or Phrase", { exact: true });
  await search.fill("a search draft"); await search.press("Control+3");
  await expect(search).toHaveValue("a search draft");
  await expect(page.locator(".reader-workspace")).toHaveAttribute("data-reader-theme", "sepia");
});

test("font and view changes keep the current passage visible", async ({ page }) => {
  await openPreparedReader(page); await setLanguage(page, "en");
  const passage = page.frameLocator(".reader-frame").locator("#paragraph-25");
  await passage.evaluate(element => element.scrollIntoView());
  const visible = () => passage.evaluate(element => Array.from(element.getClientRects()).some(rect => rect.right > 0 && rect.left < innerWidth && rect.bottom > 0 && rect.top < innerHeight));
  await expect.poll(visible).toBe(true);
  await increaseTextSize(page);
  await expect.poll(visible).toBe(true);
  for (const view of ["single", "spread", "scroll"]) {
    await setReadingView(page, view); await expect.poll(visible, { message: `The current passage remains visible in ${view} view` }).toBe(true);
  }
  // A page starts before the target passage; resizing preserves its current top text.
  const currentID = await page.frameLocator(".reader-frame").locator("p").evaluateAll(paragraphs => paragraphs.find(element => element.getBoundingClientRect().bottom > 40)?.id);
  expect(currentID).toBeTruthy();
  await page.setViewportSize({ width: 320, height: 900 });
  await expect.poll(() => page.frameLocator(".reader-frame").locator(`#${currentID}`).evaluate(element => { const rect = element.getBoundingClientRect(); return rect.bottom > 0 && rect.top < innerHeight; })).toBe(true);
});

test("book search finds text across chapters and opens the exact match without authored network requests", async ({ page }) => {
  const unexpected = []; page.on("response", response => { if (response.url().includes("reader-network-canary")) unexpected.push(response.status()); });
  await openPreparedReader(page); await setLanguage(page, "en");
  await page.getByRole("button", { name: "Search Book", exact: true }).click();
  await page.getByLabel("Word or Phrase", { exact: true }).fill("অনুচ্ছেদ 40");
  await page.getByRole("dialog").getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".reader-search-results li")).toHaveCount(2);
  await page.locator(".reader-search-results button").last().click();
  await expect(page.frameLocator(".reader-frame").getByRole("heading", { name: "দ্বিতীয় অধ্যায়", exact: true })).toBeVisible();
  await expect.poll(() => page.frameLocator(".reader-frame").locator("body").evaluate(() => document.getSelection()?.toString())).toContain("অনুচ্ছেদ 40");
  expect(unexpected).toEqual([]);
});

test("reader keyboard controls work while CSP blocks authored scripts and event handlers", async ({ page }) => {
  const session = await openPreparedReader(page), responses = [];
  const path = session.resource_base + session.chapters[0].path;
  page.on("response", response => { if (response.url().includes("authored-script-canary")) responses.push(response.status()); });
  await page.route(`**${path}`, async route => {
    const response = await route.fetch({ url: (process.env.FOUNDATION_READER_API_URL ?? "") + path });
    const payload = '<script>window.authoredScriptExecuted=true;</script><script src="/authored-script-canary.js"></script><img src="data:image/png;base64,aW52YWxpZA==" onerror="window.authoredHandlerExecuted=true" alt="" />';
    expect(response.headers()["content-security-policy"]).toContain("script-src 'none';");
    await route.fulfill({ response, body: (await response.text()).replace("</body>", payload + "</body>") });
  });
  await page.reload(); await setLanguage(page, "en");
  const content = page.frameLocator(".reader-frame");
  await setReadingView(page, "single");
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } }); await page.keyboard.press("ArrowLeft");
  await expect.poll(() => content.locator("html").evaluate(root => root.scrollLeft)).toBe(0);
  expect(await content.locator("body").evaluate(() => ({ script: window.authoredScriptExecuted, handler: window.authoredHandlerExecuted }))).toEqual({ script: undefined, handler: undefined });
  expect(responses).toEqual([]);
});

test("book search reports unavailable chapters and can be retried", async ({ page }) => {
  const session = await openPreparedReader(page);
  const unavailable = `**${session.resource_base}${session.chapters[1].path}`;
  await page.route(unavailable, route => route.fulfill({ status: 503 }));
  await setLanguage(page, "en");
  await page.getByRole("button", { name: "Search Book", exact: true }).click();
  await page.getByLabel("Word or Phrase", { exact: true }).fill("অনুচ্ছেদ 40");
  await page.getByRole("dialog").getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText("Some chapters could not be searched. Please try again.");
  await page.unroute(unavailable);
  await page.getByRole("dialog").getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.locator(".reader-search-results li")).toHaveCount(2);
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveCount(0);
});

test("public book details put reading controls before metadata and open the actual reader", async ({ page }) => {
  await useAccount(page, "reading_reader"); await readerAPI(page);
  await page.goto(`/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  for (const language of ["English", "বাংলা"]) {
    await setLanguage(page, language === "English" ? "en" : "bn");
    const actions = page.locator(".book-primary-actions");
    const read = actions.getByRole("button", { name: /^(Read Book|বই পড়ুন)$/ }).or(actions.getByRole("link", { name: /^(Continue Reading|পড়া চালিয়ে যান)$/ }));
    await expect(read).toBeVisible();
    const button = await read.boundingBox(), facts = await page.locator(".book-facts").first().boundingBox();
    expect(button.y + button.height).toBeLessThan(facts.y);
    if ((await page.viewportSize()).width <= 767) expect(button.y + button.height).toBeLessThan((await page.viewportSize()).height);
  }
  await page.locator(".book-primary-actions").getByRole("button", { name: "বই পড়ুন", exact: true }).or(page.locator(".book-primary-actions").getByRole("link", { name: "পড়া চালিয়ে যান", exact: true })).click();
  await expect(page).toHaveURL(/\/reader\/[0-9a-f-]+\/$/);
  await expect(page.frameLocator(".reader-frame").locator("body")).not.toBeEmpty();
});

test("book details show saved reading progress and only that book's personal notes", async ({ page }) => {
  await useAccount(page, "update_reader"); const origin = await readerAPI(page);
  const account = await (await page.request.get(`${origin}/api/v1/auth/session/`)).json();
  const launched = await page.request.post(`${origin}/api/v1/reading/books/${encodeURIComponent(fixture.update_book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(launched.status()).toBe(200); const session = await launched.json();
  const headers = { "X-CSRFToken": account.csrf_token };
  expect((await page.request.put(`${origin}/api/v1/reading/sessions/${session.id}/progress/`, { headers, data: { last_location: "chapter:0:0.5", progress_percent: 25 } })).status()).toBe(200);
  const note = `Book detail note ${crypto.randomUUID()}`;
  expect((await page.request.post(`${origin}/api/v1/reading/sessions/${session.id}/highlights/`, { headers, data: { chapter_href: session.chapters[0].path, selector: { start: 0, end: 4 }, text: "বাংলা", note } })).status()).toBe(201);
  await page.goto(`/books/${encodeURIComponent(fixture.update_book.slug)}/`);
  await setLanguage(page, "en");
  const summary = page.locator(".book-reading-summary");
  await expect(summary.getByRole("heading", { name: "Your reading and notes", exact: true })).toBeVisible();
  await expect(summary.locator(".book-facts")).toContainText("25%");
  await expect(summary.getByText(note, { exact: true })).toBeVisible();
  await summary.locator(".annotation-card").filter({ hasText: note }).click();
  await expect(summary.getByRole("dialog").getByLabel("Your Note", { exact: true })).toHaveValue(note);
  await page.context().clearCookies(); await page.reload();
  await expect(page.locator(".book-reading-summary")).toHaveCount(0);
});
