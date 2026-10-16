import { randomBytes } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { authenticatorCode } from "../totp.mjs";
import { startSetup } from "./security-fixture.mjs";

test("profile settings require login and carry a private indexing policy", async ({ page }) => {
  await page.goto("/profile/");
  await expect(page).toHaveURL(/\/login\/\?next=%2Fprofile%2F$/);
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  await expect(page.getByRole("heading", { name: "প্রোফাইল ও নিরাপত্তা", exact: true })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
});

test("profile edits preserve other unfinished forms and normalize Kindle addresses", async ({ page }) => {
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).fill("Unfinished-Reader-Password-2026");
  await page.getByLabel("নাম", { exact: true }).fill("পাঠকের নতুন নাম");
  await page.getByRole("button", { name: "নাম সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
  await expect(page.getByLabel("নতুন পাসওয়ার্ড", { exact: true })).toHaveValue("Unfinished-Reader-Password-2026");
  await page.getByLabel("Kindle ইমেইল ঠিকানা", { exact: true }).fill("READER@KINDLE.COM\nreader@kindle.com");
  const changed = page.waitForResponse((response) => response.url().endsWith("/auth/profile/") && response.request().method() === "PATCH");
  await page.getByRole("button", { name: "ঠিকানা সংরক্ষণ করুন", exact: true }).click();
  expect((await (await changed).json()).kindle_emails).toEqual(["reader@kindle.com"]);
  await expect(page.getByLabel("নতুন পাসওয়ার্ড", { exact: true })).toHaveValue("Unfinished-Reader-Password-2026");
});

test("a stale profile edit keeps the draft and is sent once", async ({ page }) => {
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  await page.getByLabel("নাম", { exact: true }).fill("সংরক্ষণ না করা নিজের নাম");
  const profile = await (await page.request.get("/api/v1/auth/profile/")).json();
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  expect((await page.request.patch("/api/v1/auth/profile/", { headers: { "X-CSRFToken": session.csrf_token }, data: { expected_updated_at: profile.updated_at, full_name: "অন্য জানালার নাম" } })).status()).toBe(200);
  const requests = []; page.on("request", (request) => { if (request.url().endsWith("/auth/profile/") && request.method() === "PATCH") requests.push(request); });
  await page.getByRole("button", { name: "নাম সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".account-settings").getByRole("alert")).toContainText("তথ্যটি অন্য জায়গায় বদলেছে");
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("সংরক্ষণ না করা নিজের নাম");
  expect(requests).toHaveLength(1);
});

test("an interrupted authenticator setup resumes the same secret and can be cancelled", async ({ page }) => {
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  const secret = await startSetup(page, "profile_reader");
  await page.reload(); await expect(page.getByText("আগের সেটআপটি অসম্পূর্ণ আছে। পাসওয়ার্ড দিয়ে সেটি আবার খুলতে পারবেন।")).toBeVisible();
  expect(await startSetup(page, "profile_reader")).toBe(secret);
  await page.getByRole("button", { name: "সেটআপ বাতিল করুন", exact: true }).click();
  await expect(page.getByTestId("authenticator-secret")).toHaveCount(0);
  const status = await (await page.request.get("/api/v1/auth/2fa/status/")).json();
  expect(status.pending_setup).toBe(false); expect(status.enabled).toBe(false);
});

test("required authenticator setup preserves the intended private return path", async ({ page }) => {
  await useAccount(page, "required_reader"); await page.goto("/notes/");
  await expect(page).toHaveURL(/\/profile\/\?next=%2Fnotes%2F$/);
  await expect(page.getByText("এই অ্যাকাউন্টে দুই ধাপের নিরাপত্তা চালু করতে হবে। তারপর পাঠাগারে ফিরতে পারবেন।", { exact: true })).toBeVisible();
  const secret = await startSetup(page, "required_reader");
  await page.getByLabel("অ্যাপের নিরাপত্তা কোড", { exact: true }).fill(authenticatorCode(secret));
  await page.getByRole("button", { name: "কোড নিশ্চিত করুন", exact: true }).click();
  await expect(page.getByText("দুই ধাপের নিরাপত্তা চালু হয়েছে।", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "নিরাপত্তা বন্ধ করার সেটিংস", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "পাঠাগারে ফিরে যান", exact: true }).click();
  await expect(page).toHaveURL(/\/notes\/$/);
});

test("enabled authenticator expires older sessions and requires a new code at the next login", async ({ page, browser, baseURL }) => {
  const previous = await browser.newContext({ baseURL });
  await previous.addCookies([{ ...fixture.security_reader.previous_session, url: baseURL, httpOnly: true, sameSite: "Lax" }]);
  expect((await previous.request.get("/api/v1/auth/profile/")).status()).toBe(200);
  await useAccount(page, "security_reader"); await page.goto("/profile/");
  const secret = await startSetup(page, "security_reader");
  const setupTime = Date.now();
  await page.getByLabel("অ্যাপের নিরাপত্তা কোড", { exact: true }).fill(authenticatorCode(secret, setupTime));
  await page.getByRole("button", { name: "কোড নিশ্চিত করুন", exact: true }).click();
  await expect(page.getByText("দুই ধাপের নিরাপত্তা চালু হয়েছে।", { exact: true })).toBeVisible();
  expect((await page.request.get("/api/v1/auth/profile/")).status()).toBe(200);
  expect((await previous.request.get("/api/v1/auth/profile/")).status()).toBe(403);
  await previous.close();
  await page.getByRole("button", { name: "প্রস্থান", exact: true }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("link", { name: "প্রবেশ করুন", exact: true })).toBeVisible();
  await page.goto("/login/?next=%2Fnotes%2F");
  await expect(page.getByLabel("দুই ধাপের নিরাপত্তা কোড", { exact: true })).toHaveCount(0);
  await page.getByLabel("ইমেইল", { exact: true }).fill(fixture.security_reader.email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(fixture.security_reader.password);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page.locator(".account-form").getByRole("alert")).toContainText("দুই ধাপের নিরাপত্তা চালু আছে");
  await expect(page.getByLabel("দুই ধাপের নিরাপত্তা কোড", { exact: true })).toBeFocused();
  await page.getByLabel("দুই ধাপের নিরাপত্তা কোড", { exact: true }).fill(authenticatorCode(secret, setupTime + 30_000));
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page).toHaveURL(/\/notes\/$/);
});

test("changing a password keeps the current session and clears password fields", async ({ page, browser }) => {
  await useAccount(page, "profile_reader"); await page.goto("/profile/");
  const other = await browser.newContext(); const previous = await other.newPage(); await useAccount(previous, "profile_reader");
  const password = randomBytes(24).toString("base64url");
  await page.getByLabel("বর্তমান পাসওয়ার্ড", { exact: true }).fill(fixture.profile_reader.password);
  await page.getByLabel("নতুন পাসওয়ার্ড", { exact: true }).fill(password);
  await page.getByLabel("নতুন পাসওয়ার্ড আবার লিখুন", { exact: true }).fill(password);
  await page.getByRole("button", { name: "পাসওয়ার্ড বদলান", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
  await expect(page.getByLabel("বর্তমান পাসওয়ার্ড", { exact: true })).toHaveValue("");
  expect((await page.request.get("/api/v1/auth/profile/")).status()).toBe(200);
  expect((await previous.request.get("http://127.0.0.1:3000/api/v1/auth/profile/")).status()).toBe(403);
  await other.close();
});
