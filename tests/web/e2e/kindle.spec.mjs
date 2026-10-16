import { test, expect, fixture, useAccount } from "./fixtures.mjs";

const composerPath = `/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/`;

test("Kindle history requires a session and stays private", async ({ page }) => {
  await page.goto("/kindle/");
  await expect(page).toHaveURL(/\/login\/\?next=%2Fkindle%2F$/);
  await useAccount(page, "kindle_reader"); await page.goto("/kindle/");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await expect(page.getByRole("heading", { name: "কিন্ডলে পাঠানোর অনুরোধ", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "পরিচালনা", exact: true })).toHaveCount(0);
});

test("readers select recipients and cancel their own queued request on a phone", async ({ page }) => {
  await useAccount(page, "kindle_reader"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(composerPath);
  await page.getByRole("checkbox", { name: "reader@kindle.com", exact: true }).uncheck();
  const response = page.waitForResponse((reply) => reply.url().includes("/delivery/books/") && reply.request().method() === "POST");
  await page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true }).click();
  const accepted = await response;
  expect(accepted.status()).toBe(202);
  expect(accepted.request().postDataJSON().recipients).toEqual(["other@kindle.com"]);
  await page.getByRole("link", { name: "পাঠানোর অবস্থা দেখুন →", exact: true }).click();
  await expect(page.locator(".status-label")).toHaveText("পাঠানোর অপেক্ষায়");
  await expect(page.locator(".kindle-recipients")).toContainText("other@kindle.com");
  await expect(page.locator(".kindle-recipients")).not.toContainText("reader@kindle.com");
  await page.getByRole("button", { name: "পাঠানো বাতিল করুন", exact: true }).click();
  await expect(page.locator(".status-label")).toHaveText("বাতিল");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/kindle-operation-390.png", fullPage: true });
});

test("invalid recipient selections remain editable and corrected commands keep the same identifier", async ({ page }) => {
  await useAccount(page, "kindle_reader"); await page.goto(composerPath);
  await page.getByRole("checkbox", { name: "reader@kindle.com", exact: true }).uncheck();
  await page.getByRole("checkbox", { name: "other@kindle.com", exact: true }).uncheck();
  const first = page.waitForResponse((reply) => reply.url().includes("/delivery/books/") && reply.request().method() === "POST");
  await page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true }).click();
  const invalid = await first;
  expect(invalid.status()).toBe(400);
  await expect(page.getByText("অন্তত একটি প্রোফাইলের ঠিকানা বেছে নিন। সর্বোচ্চ ১০টি ঠিকানা পাঠানো যাবে।", { exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "other@kindle.com", exact: true })).toBeEnabled();
  await page.getByRole("checkbox", { name: "other@kindle.com", exact: true }).check();
  const next = page.waitForResponse((reply) => reply.url().includes("/delivery/books/") && reply.request().method() === "POST");
  await page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true }).click();
  const corrected = await next;
  expect(corrected.status()).toBe(202);
  expect(corrected.request().postDataJSON().operation_id).toBe(invalid.request().postDataJSON().operation_id);
});

test("uncertain Kindle commands are sent once and expose their original status link", async ({ page }) => {
  await useAccount(page, "kindle_reader"); await page.goto(composerPath);
  const commands = [];
  await page.route("**/api/v1/delivery/books/*/kindle/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    commands.push(route.request().postDataJSON());
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain request", field_errors: {} }) });
  });
  await page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true }).click();
  await expect(page.locator(".account-settings").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true })).toBeDisabled();
  await expect(page.getByRole("link", { name: "এই অনুরোধের ফল দেখুন", exact: true })).toHaveAttribute("href", `/kindle/operations/${commands[0].operation_id}/`);
  expect(commands).toHaveLength(1);
});

test("Kindle operations cannot be opened by another account", async ({ page }) => {
  await useAccount(page, "kindle_reader"); await page.goto(composerPath);
  await page.getByRole("button", { name: "বই পাঠানোর অনুরোধ করুন", exact: true }).click();
  const link = page.getByRole("link", { name: "পাঠানোর অবস্থা দেখুন →", exact: true });
  await expect(link).toBeVisible(); const path = await link.getAttribute("href");
  await useAccount(page, "editor");
  expect((await page.request.get(path)).status()).toBe(404);
  expect((await page.request.get(`/api/v1/delivery/books/${fixture.reading_book.slug}/kindle/`)).status()).toBe(403);
});
