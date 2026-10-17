import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { startSetup } from "./security-fixture.mjs";
import { authenticatorCode } from "../totp.mjs";

const apiOrigin = process.env.FOUNDATION_API_URL ?? "http://127.0.0.1:8000";

test("maintenance password and optional authenticator form works without JavaScript at 320px", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 800 } });
  const page = await context.newPage(); await page.goto(`${apiOrigin}/admin/login/`);
  await expect(page.getByLabel("Authenticator code (if enabled):", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open library profile", exact: true })).toHaveAttribute("href", new URL("/profile/", process.env.FOUNDATION_WEB_URL ?? "http://127.0.0.1:3000").href);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/maintenance-login-320.png", fullPage: true });
  await page.getByLabel("Email:", { exact: true }).fill(fixture.maintenance_administrator.email);
  await page.getByLabel("Password:", { exact: true }).fill(fixture.maintenance_administrator.password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(`${apiOrigin}/admin/`);
  await context.close();
});

test("library confirmation enables maintenance and a later password-only login is rejected", async ({ page }) => {
  await useAccount(page, "maintenance_administrator"); await page.goto("/profile/");
  const secret = await startSetup(page, "maintenance_administrator");
  const setupTime = Date.now();
  await page.getByLabel("অ্যাপের নিরাপত্তা কোড", { exact: true }).fill(authenticatorCode(secret, setupTime));
  await page.getByRole("button", { name: "কোড নিশ্চিত করুন", exact: true }).click();
  await expect(page.getByText("দুই ধাপের নিরাপত্তা চালু হয়েছে।", { exact: true })).toBeVisible();
  expect((await page.request.get(`${apiOrigin}/admin/`)).status()).toBe(200);
  await page.getByRole("button", { name: "প্রস্থান", exact: true }).click(); await expect(page).toHaveURL("/");
  await page.goto(`${apiOrigin}/admin/login/`);
  await page.getByLabel("Email:", { exact: true }).fill(fixture.maintenance_administrator.email);
  await page.getByLabel("Password:", { exact: true }).fill(fixture.maintenance_administrator.password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByText("Enter a fresh authenticator code to open maintenance.", { exact: true })).toBeVisible();
  await page.getByLabel("Password:", { exact: true }).fill(fixture.maintenance_administrator.password);
  await page.getByLabel("Authenticator code (if enabled):", { exact: true }).fill(authenticatorCode(secret, setupTime + 30_000));
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(`${apiOrigin}/admin/`);
});
