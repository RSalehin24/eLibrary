import { test, expect, fixture, useAccount } from "./fixtures.mjs";

const ticketURL = (account, pathname) => `${pathname}#${new URLSearchParams({ uid: account.uid, token: account.token })}`;

test("password reset consumes its fragment link and expires prior sessions", async ({ page, browser, baseURL }) => {
  const previous = await browser.newContext({ baseURL }); const oldPage = await previous.newPage();
  await useAccount(oldPage, "password_reset_reader"); await oldPage.goto("/profile/");
  const user = fixture.password_reset_reader;
  await page.goto(ticketURL(user, "/reset-password/confirm/"));
  await expect(page.getByRole("heading", { name: "নতুন পাসওয়ার্ড দিন", exact: true })).toBeVisible();
  await expect(page.getByLabel("নতুন পাসওয়ার্ড", { exact: true })).toBeEnabled();
  expect(new URL(page.url()).hash).toBe("");
  await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).fill(user.new_password);
  await page.getByLabel("নতুন পাসওয়ার্ড আবার লিখুন", { exact: true }).fill(user.new_password);
  await page.getByRole("button", { name: "পাসওয়ার্ড সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "পাসওয়ার্ড সংরক্ষিত হয়েছে", exact: true })).toBeVisible();
  expect((await (await oldPage.request.get("/api/v1/auth/session/")).json()).authenticated).toBe(false);
  await previous.close(); await page.goto(ticketURL(user, "/reset-password/confirm/"));
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("লিংকটি ব্যবহার করা যায়নি");
  await page.goto("/login/"); await page.getByLabel("ইমেইল", { exact: true }).fill(user.email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(user.new_password);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "আমার বই", exact: true })).toBeVisible();
});

test("required invitation creates a restricted setup session at 320 pixels", async ({ page }) => {
  const user = fixture.password_setup_reader; await page.setViewportSize({ width: 320, height: 800 });
  const inspection = page.waitForResponse((response) => response.url().endsWith("/auth/password-links/inspect/") && response.request().method() === "POST");
  await page.goto(ticketURL(user, "/create-password/"));
  expect((await inspection).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "পাসওয়ার্ড তৈরি করুন", exact: true })).toBeVisible();
  await expect(page.getByText("পাসওয়ার্ডের পরে দুই ধাপের নিরাপত্তা প্রস্তুত করতে হবে।", { exact: true })).toBeVisible();
  await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).fill(user.new_password);
  await page.getByLabel("নতুন পাসওয়ার্ড আবার লিখুন", { exact: true }).fill(user.new_password);
  await page.getByRole("button", { name: "পাসওয়ার্ড সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("link", { name: "দুই ধাপের নিরাপত্তা প্রস্তুত করুন", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect((await page.request.get("/api/v1/me/books/")).status()).toBe(403);
  await page.getByRole("link", { name: "দুই ধাপের নিরাপত্তা প্রস্তুত করুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "প্রোফাইল ও নিরাপত্তা", exact: true })).toBeVisible();
  await expect(page.getByText("এই অ্যাকাউন্টে দুই ধাপের নিরাপত্তা চালু করতে হবে। তারপর পাঠাগারে ফিরতে পারবেন।", { exact: true })).toBeVisible();
});

test("password validation keeps the form editable and uncertain confirmation is never replayed", async ({ page }) => {
  const user = fixture.password_reset_reader;
  await page.route("**/api/v1/auth/password-links/inspect/", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ purpose: "reset", totp_setup_required: false }) }));
  await page.goto(ticketURL(user, "/reset-password/confirm/"));
  await expect(page.getByLabel("নতুন পাসওয়ার্ড", { exact: true })).toBeEnabled();
  const responses = [400, 503], writes = [];
  await page.route("**/api/v1/auth/password-links/confirm/", async (route) => {
    writes.push(route.request()); const status = responses.shift();
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify({ code: "invalid", detail: "Synthetic failure", field_errors: status === 400 ? { new_password: ["Choose another password."] } : {} }) });
  });
  const password = page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }), confirm = page.getByLabel("নতুন পাসওয়ার্ড আবার লিখুন", { exact: true });
  await password.fill(user.new_password); await confirm.fill(user.new_password);
  const save = page.getByRole("button", { name: "পাসওয়ার্ড সংরক্ষণ করুন", exact: true }); await save.click();
  await expect(password).toHaveAttribute("aria-invalid", "true"); await expect(save).toBeEnabled();
  await save.click(); await expect(save).toBeDisabled(); await expect.poll(() => writes.length).toBe(2);
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
});

test("invalid password links remain private and cannot submit a password", async ({ page }) => {
  const response = await page.goto("/create-password/#uid=invalid&token=invalid"); expect(response.status()).toBe(200);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await expect(page.locator(".account-form").getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: "পাসওয়ার্ড সংরক্ষণ করুন", exact: true })).toHaveCount(0);
});
