import { test, expect, fixture, useAccount } from "./fixtures.mjs";

async function login(page, account) {
  await page.goto("/login/?next=%2Fprofile%2F");
  await page.getByLabel("ইমেইল", { exact: true }).fill(fixture[account].email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(fixture[account].password);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(page).toHaveURL(/\/profile\/$/);
}

test("logout in another tab clears the cached profile and its unfinished draft", async ({ page, context }) => {
  await login(page, "reader");
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation reader");
  await page.getByLabel("নাম", { exact: true }).fill("আগের অ্যাকাউন্টের অসম্পূর্ণ নাম");
  const other = await context.newPage(); await other.goto("/my-books/");
  await other.locator("details.account-menu:visible > summary").click(); await other.getByRole("button", { name: "প্রস্থান", exact: true }).click();
  await expect(other).toHaveURL(new URL("/", other.url()).href);
  await expect(page).toHaveURL(/\/login\/\?next=%2Fprofile%2F$/);
  await expect(page.getByLabel("নাম", { exact: true })).toHaveCount(0);
  await login(other, "editor");
  await expect(page).toHaveURL(/\/profile\/$/);
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation editor");
  await other.close();
});

test("a session change outside the app clears private state on returning focus", async ({ page }) => {
  await page.addInitScript(() => { window.BroadcastChannel = undefined; });
  await login(page, "reader");
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation reader");
  await useAccount(page, "editor");
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation editor");
});

test("a cookie change before the first session response replaces the server account snapshot", async ({ page }) => {
  let release;
  let notifyStarted;
  const gate = new Promise((resolve) => { release = resolve; });
  const started = new Promise((resolve) => { notifyStarted = resolve; });
  let held = false;
  await page.route("**/api/v1/auth/session/", async (route) => {
    if (!held && new URL(route.request().headers().referer).pathname === "/profile/") {
      held = true; notifyStarted(); await gate;
      await route.fulfill({ response: await page.request.get("/api/v1/auth/session/") });
      return;
    }
    await route.continue();
  });
  await login(page, "reader");
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation reader");
  await started;
  await useAccount(page, "editor"); release();
  await expect(page.getByLabel("নাম", { exact: true })).toHaveValue("Foundation editor");
});
