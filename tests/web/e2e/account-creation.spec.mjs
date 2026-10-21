import { randomUUID } from "node:crypto";
import { test, expect, useAccount, setLanguage } from "./fixtures.mjs";
import { startSetup } from "./security-fixture.mjs";

test("superadministrators can create a password account without mail in both languages", async ({ page }) => {
  await useAccount(page, "creation_administrator");
  await page.goto("/manage/users-access/invite/");
  await setLanguage(page, "en");
  await expect(page.getByLabel("Account setup method")).toHaveValue("invite");
  await page.getByLabel("Account setup method").selectOption("password");
  await expect(page.getByRole("checkbox", { name: "Account Enabled", exact: true })).toBeChecked();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const email = `password-browser-${randomUUID()}@example.test`;
  await page.getByLabel("Reader Email", { exact: true }).fill(email);
  await page.getByLabel("Reader Name", { exact: true }).fill("Immediate password reader");
  await page.getByRole("button", { name: "Generate a secure password", exact: true }).click();
  const password = await page.getByLabel("Initial password", { exact: true }).inputValue();
  expect(password.length).toBe(51);
  await expect(page.getByLabel("Initial password", { exact: true })).toHaveAttribute("type", "password");
  await page.getByLabel("Confirm initial password", { exact: true }).fill("different-password");
  await page.getByRole("button", { name: "Create Account", exact: true }).click();
  await expect(page.getByLabel("Confirm initial password", { exact: true })).toHaveAttribute("aria-invalid", "true");
  await page.getByLabel("Confirm initial password", { exact: true }).fill(password);
  await setLanguage(page, "bn");
  await expect(page.getByLabel("অ্যাকাউন্ট তৈরির পদ্ধতি")).toHaveValue("password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট তৈরি করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "পাঠকের অ্যাকাউন্ট তৈরি হয়েছে", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "অ্যাকাউন্ট ও অনুমতি দেখুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Immediate password reader", exact: true })).toBeVisible();
  await page.locator("details.account-menu:visible > summary").click(); await page.getByRole("button", { name: "প্রস্থান", exact: true }).click();
  await expect(page.getByRole("link", { name: "প্রবেশ করুন", exact: true })).toBeVisible();
  await page.goto("/login/");
  await page.getByLabel("ইমেইল", { exact: true }).fill(email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(password);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page).toHaveURL(/\/my-books\//);
});

test("ordinary access managers keep invitation-only creation and uncertain writes stop", async ({ page }) => {
  await useAccount(page, "access_manager");
  await page.goto("/manage/users-access/invite/");
  await expect(page.locator("#account-setup-method")).toHaveCount(0);
  await expect(page.locator('input[name="password"]')).toHaveCount(0);
  await useAccount(page, "superadministrator");
  await page.goto("/manage/users-access/invite/");
  await page.getByLabel("অ্যাকাউন্ট তৈরির পদ্ধতি").selectOption("password");
  await page.getByLabel("পাঠকের ইমেইল", { exact: true }).fill(`uncertain-password-${randomUUID()}@example.test`);
  await page.getByRole("button", { name: "নিরাপদ পাসওয়ার্ড তৈরি করুন", exact: true }).click();
  await page.getByRole("checkbox", { name: "অ্যাকাউন্ট সক্রিয়", exact: true }).uncheck();
  let writes = 0;
  let attemptedActive;
  await page.route("**/api/v1/manage/users/", async route => {
    writes += 1;
    attemptedActive = route.request().postDataJSON().is_active;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", field_errors: {} }) });
  });
  const submit = page.getByRole("button", { name: "অ্যাকাউন্ট তৈরি করুন", exact: true });
  await submit.click();
  await expect(submit).toBeDisabled();
  await expect(page.getByLabel("অ্যাকাউন্ট তৈরির পদ্ধতি")).toBeDisabled();
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  expect(writes).toBe(1);
  expect(attemptedActive).toBe(false);
});

test("account sorting preserves query and status filters on phones", async ({ page }) => {
  await useAccount(page, "superadministrator");
  await page.goto("/manage/users-access/?q=foundation&status=active&sort=email_desc");
  await setLanguage(page, "en");
  await expect(page.getByLabel("Sort accounts", { exact: true })).toHaveValue("email_desc");
  await page.getByLabel("Sort accounts", { exact: true }).selectOption("name_desc");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/q=foundation&status=active&sort=name_desc/);
  await expect(page.getByLabel("Name, email or permission", { exact: true })).toHaveValue("foundation");
  await expect(page.getByLabel("Account Status", { exact: true })).toHaveValue("active");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("authenticator setup URL copying has a selectable fallback and bilingual feedback", async ({ page }) => {
  await useAccount(page, "totp_copy_reader");
  await page.goto("/profile/");
  await startSetup(page, "totp_copy_reader");
  await page.evaluate(() => {
    window.clipboardShouldFail = true;
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async value => {
      if (window.clipboardShouldFail) throw new Error("Clipboard unavailable");
      const parsed = new URL(value);
      window.copiedValidSetupURL = parsed.protocol === "otpauth:" && parsed.searchParams.get("secret") === document.querySelector('[data-testid="authenticator-secret"]').textContent;
    } } });
  });
  await page.getByRole("button", { name: "সেটআপের লিংক কপি করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "লিংক কপি করা যায়নি" })).toBeVisible();
  await expect(page.locator("details[open] .authenticator-secret")).toBeVisible();
  await page.evaluate(() => { window.clipboardShouldFail = false; });
  await page.getByRole("button", { name: "সেটআপের লিংক কপি করুন", exact: true }).click();
  expect(await page.evaluate(() => window.copiedValidSetupURL)).toBe(true);
  await setLanguage(page, "en");
  await expect(page.getByRole("status").filter({ hasText: "Setup URL copied." })).toBeVisible();
  await setLanguage(page, "bn");
  await page.getByRole("button", { name: "সেটআপ বাতিল করুন", exact: true }).click();
});
