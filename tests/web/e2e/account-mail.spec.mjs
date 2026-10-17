import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("phone invitation workflow creates a restricted reader and controls queued mail", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/manage/users-access/"); await page.getByRole("link", { name: "পাঠককে আমন্ত্রণ জানান", exact: true }).click();
  const email = `browser-invitation-${randomUUID()}@example.test`;
  await page.getByLabel("পাঠকের ইমেইল", { exact: true }).fill(email);
  await page.getByLabel("পাঠকের নাম", { exact: true }).fill("নতুন আমন্ত্রিত পাঠক");
  await page.getByLabel("দুই ধাপের নিরাপত্তা বাধ্যতামূলক", { exact: true }).check();
  const save = page.getByRole("button", { name: "আমন্ত্রণ পাঠান", exact: true });
  expect((await save.boundingBox()).height).toBeGreaterThanOrEqual(44); await save.click();
  await expect(page.getByRole("heading", { name: "আমন্ত্রণ পাঠানোর কাজ যোগ হয়েছে", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "আমন্ত্রণের অবস্থা দেখুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "আমন্ত্রণের ইমেইল", exact: true })).toBeVisible();
  const firstPath = new URL(page.url()).pathname;
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/invitation-status-390.png", fullPage: true });
  await page.getByRole("button", { name: "স্থগিত করুন", exact: true }).click(); await expect(page.locator(".status-label")).toHaveText("স্থগিত");
  await page.getByRole("button", { name: "আবার চালু করুন", exact: true }).click(); await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  await page.getByRole("button", { name: "বাতিল করুন", exact: true }).click(); await expect(page.locator(".status-label")).toHaveText("বাতিল");
  await page.getByRole("link", { name: "অ্যাকাউন্ট ও অনুমতি দেখুন", exact: true }).click();
  await expect(page.getByRole("heading", { name: "নতুন আমন্ত্রিত পাঠক", exact: true })).toBeVisible();
  await expect(page.getByText("প্রবেশ: সক্রিয় · দুই ধাপ: সেটআপ বাকি", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "নতুন আমন্ত্রণের লিংক পাঠান", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "নতুন আমন্ত্রণ পাঠানোর কাজ যোগ হয়েছে" })).toBeVisible();
  await page.getByRole("link", { name: "আমন্ত্রণের অবস্থা দেখুন", exact: true }).click();
  expect(new URL(page.url()).pathname).not.toBe(firstPath);
  await expect(page.locator(".status-label")).toHaveText("অপেক্ষমাণ");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  const identifier = new URL(page.url()).pathname.split("/").filter(Boolean).at(-1);
  await useAccount(page, "source_processor");
  expect((await page.request.get(`/api/v1/manage/mail/${identifier}/`)).status()).toBe(403);
  expect((await page.request.get(`/manage/users-access/mail/${identifier}/`)).status()).toBe(404);
});

test("invitation validation preserves editable fields and uncertain writes retain their identifier", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto("/manage/users-access/invite/");
  const email = page.getByLabel("পাঠকের ইমেইল", { exact: true }); await email.fill(fixture.managed_reader.email);
  const save = page.getByRole("button", { name: "আমন্ত্রণ পাঠান", exact: true }); await save.click();
  await expect(email).toHaveAttribute("aria-invalid", "true"); await expect(save).toBeEnabled();
  const writes = [];
  await page.route("**/api/v1/manage/invitations/", async (route) => {
    writes.push(route.request().postDataJSON()); await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain write", field_errors: {} }) });
  });
  await email.fill(`uncertain-${randomUUID()}@example.test`); await save.click();
  await expect(save).toBeDisabled(); await expect(page.locator(".account-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  expect(writes).toHaveLength(1);
  await expect(page.getByRole("link", { name: "এই অনুরোধের অবস্থা দেখুন", exact: true })).toHaveAttribute("href", `/manage/users-access/mail/${writes[0].operation_id}/`);
});

test("anonymous reset request has generic feedback and respects private session boundaries", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 }); await page.goto("/login/");
  await page.getByRole("link", { name: "পাসওয়ার্ড ভুলে গেছেন?", exact: true }).click();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true }).fill(`missing-${randomUUID()}@example.test`);
  await page.getByRole("button", { name: "পাসওয়ার্ড বদলানোর লিংক চাই", exact: true }).click();
  await expect(page.getByRole("heading", { name: "ইমেইল পরীক্ষা করুন", exact: true })).toBeVisible();
  await expect(page.getByText("এই ইমেইলে উপযুক্ত হিসাব থাকলে পাসওয়ার্ড বদলানোর লিংক পাঠানো হবে। স্প্যাম ফোল্ডারও পরীক্ষা করুন।", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await useAccount(page, "reader"); await page.goto("/reset-password/");
  await expect(page.getByRole("heading", { name: "প্রোফাইল ও নিরাপত্তা", exact: true })).toBeVisible();
});

test("uncertain reset requests stop resubmission and retain the address", async ({ page }) => {
  await page.goto("/reset-password/"); const writes = [];
  await page.route("**/api/v1/auth/password-reset/", async (route) => {
    writes.push(route.request()); await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain write", field_errors: {} }) });
  });
  const email = page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true }); await email.fill("synthetic-request@example.test");
  const save = page.getByRole("button", { name: "পাসওয়ার্ড বদলানোর লিংক চাই", exact: true }); await save.click();
  await expect(save).toBeDisabled(); await expect(email).toHaveValue("synthetic-request@example.test");
  await expect.poll(() => writes.length).toBe(1); await expect(page.locator(".account-form").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
});

test("a definitive CSRF rejection refreshes the token and retries the same reset command once", async ({ page }) => {
  const writes = [];
  await page.route("**/api/v1/auth/password-reset/", async (route) => {
    writes.push(route.request().postDataJSON());
    await route.fulfill({ status: writes.length === 1 ? 403 : 202, contentType: "application/json",
      body: JSON.stringify(writes.length === 1 ? { code: "csrf_failed", field_errors: {} } : { accepted: true }) });
  });
  await page.goto("/reset-password/");
  await page.getByLabel("অ্যাকাউন্টের ইমেইল", { exact: true }).fill("csrf-race@example.test");
  await page.getByRole("button", { name: "পাসওয়ার্ড বদলানোর লিংক চাই", exact: true }).click();
  await expect.poll(() => writes.length).toBe(2);
  expect(writes[1]).toEqual(writes[0]);
});

test("invitation forms remain usable at 320 pixels with 200 percent text", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/manage/users-access/invite/"); await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByLabel("পাঠকের ইমেইল", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "আমন্ত্রণ পাঠান", exact: true })).toBeVisible();
});
