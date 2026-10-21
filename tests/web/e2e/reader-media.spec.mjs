import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";
import { silentAudio } from "./media-fixture.mjs";

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

async function openMediaCfi(page, options) {
  await useAccount(page, "legacy_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": account.csrf_token };
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.legacy_reading.book.slug)}/launch/`, { headers });
  expect(launched.status()).toBe(200);
  const session = await launched.json(), chapter = session.chapters[0];
  const resourceURL = session.resource_base + chapter.path, audioURL = session.resource_base + "cfi-audio.wav";
  const response = await page.request.get(resourceURL);
  expect(response.status()).toBe(200);
  const source = (await response.text()).replace(/<\/body\s*>/i, options.markup.replaceAll("AUDIO_URL", audioURL) + '<div style="height:1600px"></div></body>');
  const path = await page.evaluate(source => {
    const document = new DOMParser().parseFromString(source, "application/xhtml+xml"), steps = [];
    for (let element = document.getElementById("cfi-media"); element && element !== document.documentElement; element = element.parentElement) steps.unshift((Array.from(element.parentElement.children).indexOf(element) + 1) * 2);
    return steps.map(step => `/${step}`).join("") + "[cfi-media]";
  }, source);
  const last_location = `epubcfi(/${chapter.spine_step ?? 6}/${((chapter.spine_index ?? 0) + 1) * 2}!${path}${options.suffix})`;
  const progressURL = `/api/v1/reading/sessions/${session.id}/progress/`;
  expect((await page.request.put(progressURL, { headers, data: { last_location, progress_percent: 0 } })).status()).toBe(200);
  await page.route(`**${resourceURL}`, route => route.fulfill({ body: source, contentType: "application/xhtml+xml", headers: { "Content-Security-Policy": response.headers()["content-security-policy"], "Permissions-Policy": response.headers()["permissions-policy"] } }));
  await page.route(`**${audioURL}`, route => {
    const audio = silentAudio(), range = /^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range ?? "");
    if (!range) return route.fulfill({ body: audio, contentType: "audio/wav", headers: { "Accept-Ranges": "bytes" } });
    const start = Number(range[1]), end = range[2] ? Math.min(Number(range[2]), audio.length - 1) : audio.length - 1;
    return route.fulfill({ status: 206, body: audio.subarray(start, end + 1), contentType: "audio/wav", headers: { "Accept-Ranges": "bytes", "Content-Range": `bytes ${start}-${end}/${audio.length}` } });
  });
  await page.route("**/api/v1/reading/sessions/*/progress/", route => route.fulfill({ json: route.request().postDataJSON() }));
  await page.goto(`/reader/${session.id}/`);
  await setLanguage(page, "en");
  await expect(page.locator('.reader-frame[aria-busy="false"]')).toBeVisible();
  return { session, last_location, restore: () => page.request.put(progressURL, { headers, data: session.reading_progress }) };
}

test("an original image CFI restores its percentage point and keeps the saved record intact", async ({ page }) => {
  const opened = await openMediaCfi(page, { suffix: "@50:80", markup: '<img id="cfi-media" width="200" height="2000" alt="Image with a saved reading point" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=" />' });
  try {
    const target = page.frameLocator(".reader-frame").locator("#cfi-media");
    await expect.poll(() => target.evaluate(element => {
      const rectangle = element.getBoundingClientRect();
      const renderedHeight = Math.min(rectangle.height, rectangle.width * element.naturalHeight / element.naturalWidth);
      return Math.abs(rectangle.top + (rectangle.height - renderedHeight) / 2 + renderedHeight * .8 - innerHeight / 3);
    })).toBeLessThan(5);
    await expect(page.locator(".reader-workspace").getByRole("alert")).toHaveCount(0);
    const retained = await (await page.request.get(`/api/v1/reading/sessions/${opened.session.id}/`)).json();
    expect(retained.reading_progress.last_location).toBe(opened.last_location);
  } finally { expect((await opened.restore()).status()).toBe(200); }
});

test("an original audio CFI restores seconds without autoplay and blocks external media", async ({ page }) => {
  let externalRequests = 0;
  await page.route("https://outside.test/**", route => { externalRequests++; return route.abort(); });
  const opened = await openMediaCfi(page, { suffix: "~1.75", markup: '<audio id="cfi-media" autoplay="autoplay" controls="controls" preload="metadata" src="AUDIO_URL"></audio><audio preload="auto" src="https://outside.test/forbidden.wav"></audio>' });
  try {
    const target = page.frameLocator(".reader-frame").locator("#cfi-media");
    await expect.poll(() => target.evaluate(element => element.currentTime)).toBeCloseTo(1.75, 2);
    expect(await target.evaluate(element => element.paused)).toBe(true);
    expect(externalRequests).toBe(0);
    await expect(page.locator(".reader-workspace").getByRole("alert")).toHaveCount(0);
  } finally { expect((await opened.restore()).status()).toBe(200); }
});

test("an unavailable media timestamp reports failed restoration without guessing another place", async ({ page }) => {
  const opened = await openMediaCfi(page, { suffix: "~8", markup: '<audio id="cfi-media" controls="controls" preload="metadata" src="AUDIO_URL"></audio>' });
  try {
    await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("Your notes are preserved");
    expect(await page.frameLocator(".reader-frame").locator("#cfi-media").evaluate(element => element.currentTime)).toBe(0);
    await setLanguage(page, "bn");
    await expect(page.locator(".reader-workspace").getByRole("alert")).toContainText("আপনার নোট সংরক্ষিত আছে");
  } finally { expect((await opened.restore()).status()).toBe(200); }
});
