import { test, expect, fixture, useAccount } from "./fixtures.mjs";

async function preparedReader(page) {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(response.status()).toBe(200);
  const session = await response.json();
  await page.goto(`/reader/${session.id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
  return session;
}

async function saveBookmark(page) {
  const saved = page.waitForResponse(response => response.request().method() === "PUT" && response.url().endsWith("/bookmarks/"));
  await page.getByRole("button", { name: "Bookmark This Position", exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(200);
  return response.json();
}

test("new bookmarks restore the exact passage after reopening with a different font size and viewport", async ({ page }) => {
  const session = await preparedReader(page);
  const frame = page.frameLocator(".reader-frame");
  await frame.locator("#paragraph-35").evaluate(element => element.scrollIntoView());
  const saved = await saveBookmark(page);
  expect(saved.location.startsWith("text:")).toBe(true);
  const anchor = JSON.parse(saved.location.slice(5));
  expect(anchor.quote.trim()).toBe(saved.preview_text);
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  for (let index = 0; index < 6; index += 1) await page.getByRole("button", { name: "Increase Text Size", exact: true }).click();
  await page.keyboard.press("Escape");
  await page.goto(`/books/${encodeURIComponent(fixture.reading_book.slug)}/`);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/reader/${session.id}/`);
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
  await expect(frame.locator("body")).toHaveCSS("font-size", "32px");
  await page.getByRole("button", { name: "Next Chapter", exact: true }).click();
  await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
  await page.getByRole("dialog").locator(`[data-bookmark-id="${saved.id}"]`).click();
  await expect(frame.getByRole("heading", { name: "প্রথম অধ্যায়", exact: true })).toBeVisible();
  await expect.poll(() => frame.locator("body").evaluate((body, anchor) => {
    const doc = body.ownerDocument, walker = doc.createTreeWalker(body, NodeFilter.SHOW_TEXT, { acceptNode: node => node.parentElement.closest("script,style,noscript,template") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    let offset = 0, started = false;
    const range = doc.createRange();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!started && anchor.offset < offset + node.length) { range.setStart(node, anchor.offset - offset); started = true; }
      if (started && anchor.offset + anchor.quote.length <= offset + node.length) { range.setEnd(node, anchor.offset + anchor.quote.length - offset); break; }
      offset += node.length;
    }
    return range.toString() === anchor.quote && Array.from(range.getClientRects()).some(rect => rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth);
  }, anchor)).toBe(true);
  await expect(page.locator(".reader-workspace").getByRole("alert")).toHaveCount(0);
  await page.screenshot({ path: `test-artifacts/foundation/bookmark-precision-${test.info().project.name}.png` });
});

test("text bookmark restoration refuses a changed quotation and retains the original bookmark", async ({ page }) => {
  const session = await preparedReader(page);
  await page.frameLocator(".reader-frame").locator("#paragraph-25").evaluate(element => element.scrollIntoView());
  const saved = await saveBookmark(page);
  const anchor = JSON.parse(saved.location.slice(5));
  await page.route(`**${session.resource_base}${session.chapters[0].path}`, async route => {
    const response = await route.fetch();
    const source = await response.text(), changed = source.replaceAll(anchor.quote, "পরিবর্তিত লেখার অংশ");
    expect(changed !== source).toBe(true);
    await route.fulfill({ response, body: changed });
  });
  await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
  await page.getByRole("dialog").locator(`[data-bookmark-id="${saved.id}"]`).click();
  await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
  const collection = await (await page.request.get(`/api/v1/reading/sessions/${session.id}/bookmarks/`)).json();
  expect(collection.entries.find(entry => entry.id === saved.id).location).toBe(saved.location);
});

test("image-only bookmark positions explicitly describe their approximate fallback", async ({ page }) => {
  const session = await preparedReader(page);
  await page.route(`**${session.resource_base}${session.chapters[0].path}`, async route => {
    const response = await route.fetch();
    await route.fulfill({ response, body: (await response.text()).replace(/<body[^>]*>[\s\S]*<\/body>/i, '<body><img width="200" height="200" alt="Cover" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=" /></body>') });
  });
  await page.goto(`/reader/${session.id}/`);
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
  const saved = await saveBookmark(page);
  expect(saved.location.startsWith("chapter:")).toBe(true);
  await expect(page.getByText("No text position could be captured here. The bookmark stores an approximate page position.", { exact: true })).toBeVisible();
});
