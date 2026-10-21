import { test, expect } from "./fixtures.mjs";

const securityCodeLabel = "দুই ধাপের নিরাপত্তা কোড";

async function enterCredentials(page) {
  await page.goto("/login/");
  await page.getByLabel("ইমেইল", { exact: true }).fill("login-ui@example.test");
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill("Synthetic-password-for-interface");
}

async function failLogin(route, code, status = 400) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify({ code, detail: "Synthetic login response", field_errors: {} }) });
}

test("login hides the security code initially and after invalid credentials", async ({ page }) => {
  await page.route("**/api/v1/auth/login/", (route) => failLogin(route, "invalid_credentials", 403));
  await enterCredentials(page);
  await expect(page.getByLabel(securityCodeLabel, { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("ইমেইল ও পাসওয়ার্ড পরীক্ষা");
  await expect(page.getByLabel(securityCodeLabel, { exact: true })).toHaveCount(0);
});

test("an enabled-account challenge focuses the code and preserves it through a temporary failure", async ({ page }) => {
  const responses = [["otp_required", 400], ["otp_invalid", 400], ["unavailable", 503]];
  await page.route("**/api/v1/auth/login/", (route) => failLogin(route, ...responses.shift()));
  await enterCredentials(page);
  const submit = page.getByRole("button", { name: "প্রবেশ করুন", exact: true });
  await submit.click();
  const code = page.getByLabel(securityCodeLabel, { exact: true });
  await expect(code).toBeFocused(); await expect(code).toHaveAttribute("required", "");
  await code.fill("123456"); await submit.click();
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("নিরাপত্তা কোডটি সঠিক নয়");
  await expect(code).toHaveValue("123456");
  await code.fill("12345678"); await submit.click();
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("কিছুক্ষণ পরে");
  await expect(code).toHaveValue("12345678");
});

test("changing either credential discards the previous account's challenge", async ({ page }) => {
  await page.route("**/api/v1/auth/login/", (route) => failLogin(route, "otp_required"));
  await enterCredentials(page);
  for (const [label, value] of [["ইমেইল", "other-login-ui@example.test"], ["পাসওয়ার্ড", "Different-synthetic-password"]]) {
    await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
    await expect(page.getByLabel(securityCodeLabel, { exact: true })).toBeVisible();
    await page.getByLabel(label, { exact: true }).fill(value);
    await expect(page.getByLabel(securityCodeLabel, { exact: true })).toHaveCount(0);
    await expect(page.locator(".account-form").getByRole("alert")).toHaveCount(0);
  }
});

test("the login and shared branding fit a 320-pixel screen with enlarged text", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 }); await page.goto("/login/");
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await expect(page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ করুন", exact: true })).toBeVisible();
  await expect(page.locator(".site-header").getByRole("img", { name: "বাংলা পাঠাগার", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
