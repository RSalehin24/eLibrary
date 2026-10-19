import { test, expect } from "./fixtures.mjs";
import { localEPUB } from "./local-epub-fixture.mjs";

test("local EPUBs stay in the browser and support contents, typography, views and immersive reading", async ({ page }) => {
  const writes = [], external = [], errors = [];
  page.on("request", request => { if (request.method() !== "GET") writes.push(request.url()); if (request.url().includes("should-not-load.invalid")) external.push(request.url()); });
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/local-reader/");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.getByLabel("Choose an EPUB File", { exact: true }).setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: localEPUB() });
  const body = page.frameLocator(".local-reader-frame").locator("body");
  await expect(body).toContainText("প্রথম অধ্যায়");
  await expect(page.getByRole("heading", { name: "নিজের বাংলা বই", exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.localFileScriptRan)).toBeUndefined();
  await page.getByRole("button", { name: "Reading Settings", exact: true }).click();
  await page.getByLabel("Page Theme", { exact: true }).selectOption("dark");
  await page.getByLabel("Reading View", { exact: true }).selectOption("single");
  await page.getByRole("button", { name: "Increase Text Size", exact: true }).click();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(body).toHaveCSS("font-size", "22px");
  await expect(body).toHaveCSS("background-color", "rgb(24, 34, 30)");
  await page.getByRole("button", { name: "Table of Contents", exact: true }).click();
  await page.getByRole("button", { name: "দ্বিতীয় অধ্যায়", exact: true }).click();
  await expect(body).toContainText("শেষ অধ্যায়ের সম্পূর্ণ বাংলা লেখা");
  const supported = await page.evaluate(() => document.fullscreenEnabled === true);
  await page.getByRole("button", { name: supported ? "Fullscreen" : "Focus Mode", exact: true }).click();
  await expect(page.locator("button:visible")).toHaveCount(0);
  await body.click(); await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Close Book", exact: true })).toBeVisible();
  expect(writes).toEqual([]); expect(external).toEqual([]); expect(errors).toEqual([]);
});

test("malformed local EPUBs show a useful error and another file can be selected", async ({ page }) => {
  await page.goto("/local-reader/");
  const picker = page.getByLabel("EPUB ফাইল বেছে নিন", { exact: true });
  await picker.setInputFiles({ name: "broken.epub", mimeType: "application/epub+zip", buffer: Buffer.from("broken") });
  await expect(page.locator(".local-reader-start").getByRole("alert")).toContainText("এই EPUB খোলা যায়নি");
  await picker.setInputFiles({ name: "book.epub", mimeType: "application/epub+zip", buffer: localEPUB() });
  await expect(page.frameLocator(".local-reader-frame").locator("body")).toContainText("প্রথম অধ্যায়");
});

test("the public local-file reader opens offline without caching account or book responses", async ({ page, context }) => {
  await page.goto("/local-reader/");
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await context.setOffline(true);
  try {
    await page.reload();
    await expect(page.getByRole("heading", { name: "নিজের EPUB পড়ুন", exact: true })).toBeVisible();
    await page.getByLabel("EPUB ফাইল বেছে নিন", { exact: true }).setInputFiles({ name: "offline.epub", mimeType: "application/epub+zip", buffer: localEPUB() });
    await expect(page.frameLocator(".local-reader-frame").locator("body")).toContainText("প্রথম অধ্যায়");
    const cached = await page.evaluate(async () => (await Promise.all((await caches.keys()).filter(name => name.startsWith("library-static-")).map(async name => (await (await caches.open(name)).keys()).map(request => new URL(request.url).pathname)))).flat());
    expect(cached.every(path => path.startsWith("/_next/static/") || /^\/(offline|local-reader-shell)\.[a-f0-9]+\.html$/.test(path))).toBe(true);
  } finally { await context.setOffline(false); }
});

test.use({ serviceWorkers: "allow" });
