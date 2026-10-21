import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount, artifactPath, setLanguage } from "./fixtures.mjs";

test("notes separate four views, search, group by book and safely recolor", async ({ page }) => {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const response = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers });
  expect(response.status()).toBe(200);
  const session = await response.json(), unique = `notes-${randomUUID()}`;
  const identifiers = [];
  let bookmark;
  try {
    for (const values of [{ kind: "highlight", color: "yellow", note: "" }, { kind: "highlight", color: "green", note: unique }, { kind: "quote", color: "pink", note: unique }]) {
      const created = await page.request.post(`/api/v1/reading/sessions/${session.id}/highlights/`, { headers, data: { ...values, chapter_href: session.chapters[0].path, selector: { start: 0, end: 4 }, text: unique } });
      expect(created.status()).toBe(201); identifiers.push((await created.json()).id);
    }
    const saved = await page.request.put(`/api/v1/reading/sessions/${session.id}/bookmarks/`, { headers, data: { chapter_href: session.chapters[0].path, location: `chapter:0:${(parseInt(randomUUID().slice(0, 4), 16) / 65536).toFixed(4)}`, note: unique } });
    expect(saved.status()).toBe(200); bookmark = (await saved.json()).id;
    await page.goto("/notes/");
    await setLanguage(page, "en");
    await page.getByRole("searchbox", { name: "Search notes", exact: true }).fill(unique);
    await expect(page.locator(".annotation-card")).toHaveCount(1);
    for (const name of ["Highlights", "Quotes", "Bookmarks", "Notes"]) {
      await page.getByRole("button", { name: new RegExp(`^${name}\\s*\\d*$`) }).click();
      await expect(page.locator(".annotation-card")).toHaveCount(1);
    }
    await expect(page.locator(".notes-book-group h2 a")).toHaveText(fixture.reading_book.title);
    await page.getByRole("combobox", { name: "Color", exact: true }).selectOption("green");
    await expect(page.locator(".annotation-card")).toHaveCount(1);
    await page.locator(".annotation-card").click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("combobox", { name: "Color", exact: true }).selectOption("blue");
    await dialog.getByRole("textbox", { name: "Your Note", exact: true }).press("Control+Enter");
    await expect(dialog).not.toBeVisible();
    await expect(page.locator(".annotation-card")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "No matching notes", exact: true })).toBeVisible();
    await page.getByRole("combobox", { name: "Color", exact: true }).selectOption("blue");
    await expect(page.locator(".annotation-card")).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: artifactPath(`notes-workflow-${test.info().project.name}.png`), fullPage: true });
  } finally {
    for (const identifier of identifiers) await page.request.delete(`/api/v1/me/highlights/${identifier}/`, { headers });
    if (bookmark) await page.request.delete(`/api/v1/me/bookmarks/${bookmark}/`, { headers });
  }
});

test("all four personal annotation views open the exact saved passage in the reader", async ({ page }) => {
  await useAccount(page, "reading_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/launch/`, { headers });
  const session = await launched.json(), unique = `reader-notes-${randomUUID()}`, records = [];
  await page.goto(`/reader/${session.id}/`);
  await setLanguage(page, "en");
  await page.getByRole("button", { name: "Next Chapter", exact: true }).click();
  const frame = page.frameLocator(".reader-frame");
  const target = await frame.locator("#paragraph-38").evaluate(element => {
    const doc = element.ownerDocument, walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, { acceptNode: node => node.parentElement.closest("script,style,noscript,template") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    let start = 0;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node === element.firstChild) return { start, end: start + 18, text: node.textContent.slice(0, 18) };
      start += node.textContent.length;
    }
    throw new Error("Passage text is missing");
  });
  try {
    for (const values of [{ view: "Highlights", kind: "highlight", note: "" }, { view: "Notes", kind: "highlight", note: unique }, { view: "Quotes", kind: "quote", note: unique }]) {
      const response = await page.request.post(`/api/v1/reading/sessions/${session.id}/highlights/`, { headers, data: { kind: values.kind, note: values.note, chapter_href: session.chapters[1].path, chapter_label: unique, selector: { start: target.start, end: target.end }, text: target.text } });
      expect(response.status()).toBe(201); records.push({ view: values.view, kind: "highlights", id: (await response.json()).id });
    }
    const bookmark = await page.request.put(`/api/v1/reading/sessions/${session.id}/bookmarks/`, { headers, data: { chapter_href: session.chapters[1].path, chapter_label: unique, location: `text:${JSON.stringify({ chapter: 1, offset: target.start, quote: target.text })}` } });
    expect(bookmark.status()).toBe(200); records.push({ view: "Bookmarks", kind: "bookmarks", id: (await bookmark.json()).id });
    for (const record of records) {
      await page.goto("/notes/");
      await page.getByRole("button", { name: new RegExp(`^${record.view}\\s*\\d*$`) }).click();
      await page.getByRole("searchbox", { name: "Search notes", exact: true }).fill(unique);
      const card = page.locator(`[data-annotation-id="${record.id}"]`);
      await expect(card).toBeVisible();
      await card.locator("..").getByRole("button", { name: "Open in Reader", exact: true }).click();
      await expect(page).toHaveURL(new RegExp(`/reader/[0-9a-f-]+/\\?(?:bookmark|highlight)=${record.id}$`));
      await expect(frame.getByRole("heading", { name: "দ্বিতীয় অধ্যায়", exact: true })).toBeVisible();
      await expect.poll(() => frame.locator("#paragraph-38").evaluate(element => element.getBoundingClientRect().bottom > 0 && element.getBoundingClientRect().top < innerHeight)).toBe(true);
      if (record.kind === "highlights") await expect.poll(() => frame.locator("body").evaluate(body => body.ownerDocument.getSelection()?.toString())).toBe(target.text);
      await expect(page.locator(".reader-workspace").getByRole("alert")).toHaveCount(0);
    }
    const highlight = records[0];
    await page.goto("/notes/");
    await page.getByRole("button", { name: /^Highlights\s*\d*$/ }).click();
    await page.getByRole("searchbox", { name: "Search notes", exact: true }).fill(unique);
    await page.route(`**/api/v1/reading/sessions/*/resources/${session.chapters[1].path}`, async route => {
      const response = await route.fetch(), original = await response.text();
      const changed = original.replaceAll(target.text, "পরিবর্তিত লেখার অংশ");
      expect(changed).not.toBe(original);
      await route.fulfill({ response, body: changed });
    });
    await page.locator(`[data-annotation-id="${highlight.id}"]`).locator("..").getByRole("button", { name: "Open in Reader", exact: true }).click();
    await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
    const preserved = await page.request.get(`/api/v1/me/highlights/${highlight.id}/`);
    expect((await preserved.json()).text).toBe(target.text);
    await page.goto(`/reader/${session.id}/`);
    await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
    await expect(page.locator(".reader-workspace").getByRole("alert")).toHaveCount(0);
    await page.getByRole("button", { name: "Bookmarks & Highlights", exact: true }).click();
    await page.getByRole("dialog").getByRole("button").filter({ hasText: target.text }).first().click();
    await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
  } finally {
    for (const record of records) await page.request.delete(`/api/v1/me/${record.kind}/${record.id}/`, { headers });
  }
});
