import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { UpdateProxy } from "../update-proxy.mjs";
import { startSetup } from "./security-fixture.mjs";
import { configureInstallationSimulator, offerInstallation } from "../install-simulator.mjs";

test.use({ serviceWorkers: "allow" });

const proxy = new UpdateProxy();
test.beforeAll(() => proxy.start());
test.afterAll(() => proxy.stop());

async function controlled(page) {
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
}

test("root manifest supplies standalone launch and correctly sized maskable icons", async ({ page }) => {
  const response = await page.request.get("/manifest.webmanifest");
  expect(response.status()).toBe(200);
  const manifest = await response.json();
  expect(manifest.id).toBe("/"); expect(manifest.lang).toBe("bn");
  expect(manifest.start_url).toBe("/"); expect(manifest.scope).toBe("/"); expect(manifest.display).toBe("standalone");
  expect(manifest.icons.some((icon) => icon.purpose === "maskable")).toBe(true);
  expect(manifest.icons.every((icon) => /book-(192|512)-v2\.png$/.test(icon.src))).toBe(true);
  expect(manifest.screenshots).toHaveLength(2);
  for (const icon of [...manifest.icons, ...manifest.screenshots]) {
    const result = await page.request.get(icon.src); expect(result.status()).toBe(200);
    const bytes = await result.body(); const [width, height] = icon.sizes.split("x").map(Number);
    expect(bytes.readUInt32BE(16)).toBe(width); expect(bytes.readUInt32BE(20)).toBe(height);
  }
  for (const size of [192, 512]) {
    const previous = await page.request.get(`/icons/book-${size}-v1.png`);
    expect(previous.status()).toBe(200);
    expect(previous.headers()["cache-control"]).toContain("immutable");
  }
  await page.goto("/help/#install");
  await expect(page.getByText("iPhone-এ Safari", { exact: false })).toContainText("Open as Web App");
});

test("public installation previews show the Bengali workspace at phone and desktop sizes", async ({ page }) => {
  for (const [name, width, height] of [["phone", 390, 844], ["desktop", 1280, 720]]) {
    await page.setViewportSize({ width, height }); await page.goto("/");
    await expect(page.getByRole("heading", { name: "আপনার পরের বইটি খুঁজুন" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-artifacts/foundation/install-${name}.png` });
  }
});

test("offline launch shows a notice and service-worker caches exclude private responses", async ({ page, context }) => {
  await useAccount(page, "reader"); await page.goto(`${proxy.origin}/my-books/`); await controlled(page);
  await page.request.get("/api/v1/auth/session/");
  const cached = await page.evaluate(async () => (await Promise.all((await caches.keys()).filter((name) => name.startsWith("library-static-")).map(async (name) => (await (await caches.open(name)).keys()).map((request) => new URL(request.url).pathname)))).flat());
  expect(cached.length).toBeGreaterThan(0);
  expect(cached.every((path) => path.startsWith("/_next/static/") || /^\/(offline|local-reader-shell)\.[a-f0-9]+\.html$/.test(path))).toBe(true);
  proxy.offline = true;
  try {
    await context.setOffline(true); await page.goto(`${proxy.origin}/my-books/`);
    await expect(page.getByRole("heading", { name: "ইন্টারনেট সংযোগ প্রয়োজন" })).toBeVisible();
    await expect(page.getByText(fixture.book.title, { exact: true })).not.toBeVisible();
  } finally { proxy.offline = false; await context.setOffline(false); }
  await page.getByRole("link", { name: "আবার চেষ্টা করুন" }).click();
  await expect(page.getByRole("heading", { name: "আমার বই", exact: true })).toBeVisible();
});

test("an accepted update waits for unsaved editorial work and leaves other tabs open", async ({ page }) => {
  await useAccount(page, "editor");
  await page.goto(`${proxy.origin}/manage/books/${encodeURIComponent(fixture.conflict_book.slug)}/`); await controlled(page);
  const otherPage = await page.context().newPage(); await otherPage.goto(`${proxy.origin}/catalog/`);
  const field = page.getByLabel("সংক্ষিপ্ত বিবরণ", { exact: true });
  const note = [await field.inputValue(), "হালনাগাদের আগে সংরক্ষিত"].filter(Boolean).join(" · ");
  await field.fill(note);
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন" });
  await expect(update).toBeVisible();
  await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(field).toHaveValue(note);
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" }).click();
  await expect(page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন" })).toBeDisabled();
  let otherNavigations = 0; otherPage.on("framenavigated", (frame) => { if (frame === otherPage.mainFrame()) otherNavigations += 1; });
  const reloaded = page.waitForEvent("load"); await update.click(); await reloaded;
  await expect(field).toHaveValue(note);
  expect(otherNavigations).toBe(0);
  await otherPage.close();
});

test("install controls prompt only after a click and remember dismissal", async ({ page }) => {
  await page.goto("/help/"); await controlled(page);
  await offerInstallation(page, "dismissed");
  const install = page.getByRole("button", { name: "অ্যাপ ইনস্টল করুন", exact: true });
  await expect(install).toBeVisible(); expect(await page.evaluate(() => window.installPromptCount)).toBe(0);
  await install.click(); await expect(install).not.toBeVisible();
  expect(await page.evaluate(() => window.installPromptCount)).toBe(1);
  await page.evaluate(() => window.dispatchEvent(new Event("beforeinstallprompt", { cancelable: true })));
  await expect(install).not.toBeVisible();
});

test("accepted installation and standalone relaunch hide installation controls", async ({ page }) => {
  await configureInstallationSimulator(page);
  await page.goto("/help/"); await controlled(page);
  await offerInstallation(page, "accepted");
  const install = page.getByRole("button", { name: "অ্যাপ ইনস্টল করুন", exact: true });
  await expect(install).toBeVisible();
  expect(await page.evaluate(() => window.installPromptCount)).toBe(0);
  await install.click();
  await expect(install).not.toBeVisible();
  expect(await page.evaluate(() => window.installPromptCount)).toBe(1);
  await page.evaluate(() => window.simulateAppMode(true));
  await page.reload(); await controlled(page);
  await offerInstallation(page, "accepted");
  await expect(install).not.toBeVisible();
  await expect(page.locator(".pwa-controls").getByRole("link", { name: "ইনস্টলের সহায়তা", exact: true })).not.toBeVisible();
});

test("uninstalled app can be installed again after a browser relaunch", async ({ page }) => {
  await configureInstallationSimulator(page);
  await page.goto("/help/"); await controlled(page);
  await page.evaluate(() => window.simulateAppMode(true));
  await page.reload(); await controlled(page);
  await page.evaluate(() => window.simulateAppMode(false));
  await page.reload(); await controlled(page);
  await offerInstallation(page, "accepted");
  const install = page.getByRole("button", { name: "অ্যাপ ইনস্টল করুন", exact: true });
  await expect(install).toBeVisible();
  await install.click();
  await expect(install).not.toBeVisible();
  expect(await page.evaluate(() => window.installPromptCount)).toBe(1);
  expect(await page.evaluate(() => localStorage.getItem("library-install-dismissed"))).toBeNull();
});

test("accepted reader updates save the latest position before reloading", async ({ page }) => {
  await useAccount(page, "update_reader");
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const launched = await page.request.post(`/api/v1/reading/books/${encodeURIComponent(fixture.update_book.slug)}/launch/`, { headers: { "X-CSRFToken": account.csrf_token } });
  expect(launched.status()).toBe(200); const session = await launched.json();
  await page.goto(`${proxy.origin}/reader/${session.id}/`); await controlled(page);
  await expect(page.locator(".reader-frame")).toHaveAttribute("aria-busy", "false");
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন" }); await expect(update).toBeVisible();
  const fullscreen = await page.evaluate(() => document.fullscreenEnabled === true);
  await page.getByRole("button", { name: fullscreen ? "পূর্ণ পর্দা" : "শুধু বই দেখুন", exact: true }).click();
  await expect(update).not.toBeVisible();
  await expect(page.locator(".reader-toolbar")).not.toBeVisible();
  await expect(page.locator("button:visible")).toHaveCount(0);
  await page.locator(".reader-frame").click({ position: { x: 100, y: 80 } });
  await page.keyboard.press("Escape");
  await expect(update).toBeVisible();
  await page.frameLocator(".reader-frame").locator("body").evaluate(() => { const root = document.scrollingElement; root.scrollTop = (root.scrollHeight - root.clientHeight) * .4; });
  await expect(page.getByText("অবস্থান সংরক্ষণ হচ্ছে…", { exact: true })).toBeVisible();
  const saved = page.waitForResponse((response) => response.url().endsWith("/progress/") && response.request().method() === "PUT" && response.status() === 200);
  const reloaded = page.waitForEvent("load"); await update.click(); await saved; await reloaded;
  const persisted = await (await page.request.get(`/api/v1/reading/sessions/${session.id}/`)).json();
  expect(persisted.reading_progress.progress_percent).toBeGreaterThan(19);
  expect(persisted.reading_progress.progress_percent).toBeLessThan(21);
});

test("blocked preference storage shows installation help without an uncaught error", async ({ page }) => {
  const errors = []; page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/help/"); await controlled(page);
  await page.evaluate(() => {
    Object.defineProperty(window, "localStorage", { configurable: true, get: () => { throw new DOMException("Blocked", "SecurityError"); } });
    window.dispatchEvent(new Event("beforeinstallprompt", { cancelable: true }));
  });
  await expect(page.locator(".pwa-controls [role=status]")).toContainText("অ্যাপের সুবিধা প্রস্তুত হয়নি");
  await expect(page.getByRole("link", { name: "ইনস্টলের সহায়তা", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("app updates wait for profile drafts and an unconfirmed authenticator", async ({ page }) => {
  await useAccount(page, "reader"); await page.goto(`${proxy.origin}/profile/`); await controlled(page);
  await page.getByLabel("নাম", { exact: true }).fill("অসম্পূর্ণ প্রোফাইলের লেখা");
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন", exact: true });
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("অসম্পূর্ণ প্রোফাইলের লেখা");
  await page.getByRole("button", { name: "লেখা বাদ দিন", exact: true }).click();
  await startSetup(page, "reader"); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByTestId("authenticator-secret")).toBeVisible();
  await page.getByRole("button", { name: "সেটআপ বাতিল করুন", exact: true }).click();
  await expect(page.getByTestId("authenticator-secret")).toHaveCount(0);
  const reloaded = page.waitForEvent("load"); await update.click(); await reloaded;
  await expect(page.getByRole("heading", { name: "প্রোফাইল ও নিরাপত্তা", exact: true })).toBeVisible();
});

test("app updates keep an unfinished Kindle recipient selection", async ({ page }) => {
  await useAccount(page, "kindle_reader"); await page.goto(`${proxy.origin}/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/`); await controlled(page);
  await page.getByRole("checkbox", { name: "reader@kindle.com", exact: true }).uncheck();
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন", exact: true });
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByRole("checkbox", { name: "reader@kindle.com", exact: true })).not.toBeChecked();
});

test("app updates preserve unfinished access management forms", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto(`${proxy.origin}/manage/users-access/${fixture.managed_reader.id}/`); await controlled(page);
  await page.getByLabel("পাঠকের নাম", { exact: true }).fill("সংরক্ষণ না করা নাম");
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন", exact: true });
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByLabel("পাঠকের নাম", { exact: true })).toHaveValue("সংরক্ষণ না করা নাম");
  await page.getByRole("button", { name: "পরিবর্তন বাতিল করুন", exact: true }).click();
  await page.getByLabel("অনুমতির মন্তব্য", { exact: true }).fill("নতুন অনুমতির লেখা");
  await update.click(); await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByLabel("অনুমতির মন্তব্য", { exact: true })).toHaveValue("নতুন অনুমতির লেখা");
});

test("app updates preserve an unfinished password-link form", async ({ page }) => {
  await page.route("**/api/v1/auth/password-links/inspect/", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ purpose: "setup", totp_setup_required: false }) }));
  await page.goto(`${proxy.origin}/create-password/#uid=synthetic&token=synthetic`); await controlled(page);
  await expect(page.getByLabel("নতুন পাসওয়ার্ড", { exact: true })).toBeEnabled();
  await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).fill("Unfinished-password-draft-17!");
  proxy.revision += 1;
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন", exact: true });
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  expect((await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).inputValue()).length).toBe(29);
});

test("app updates preserve unfinished invitation and reset requests", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto(`${proxy.origin}/manage/users-access/invite/`); await controlled(page);
  await page.getByLabel("পাঠকের ইমেইল", { exact: true }).fill("unfinished-invitation@example.test");
  proxy.revision += 1; await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  const update = page.getByRole("button", { name: "হালনাগাদ করে আবার খুলুন", exact: true });
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByLabel("পাঠকের ইমেইল", { exact: true })).toHaveValue("unfinished-invitation@example.test");
  await page.context().clearCookies(); page.on("dialog", (dialog) => dialog.accept());
  await page.goto(`${proxy.origin}/reset-password/`); await controlled(page);
  await page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true }).fill("unfinished-reset@example.test");
  proxy.revision += 1; await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
  await expect(update).toBeVisible(); await update.click();
  await expect(page.locator(".pwa-controls").getByRole("alert")).toContainText("অসম্পূর্ণ লেখা আগে সংরক্ষণ করুন");
  await expect(page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true })).toHaveValue("unfinished-reset@example.test");
});
