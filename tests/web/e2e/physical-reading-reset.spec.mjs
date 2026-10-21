import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

const logValues = { status: "reading", current_page: 25, total_pages: 100, rating: 4, started_on: "2026-01-01", finished_on: null, notes: "সংরক্ষিত ব্যক্তিগত নোট" };

async function openSavedReadingLog(page) {
  await useAccount(page, "personal_reader");
  const path = `/api/v1/me/books/${encodeURIComponent(fixture.personal.paper.slug)}/physical-log/`;
  const previous = await (await page.request.get(path)).json();
  const account = await (await page.request.get("/api/v1/auth/session/")).json();
  const saved = await page.request.put(path, { headers: { "X-CSRFToken": account.csrf_token }, data: { ...logValues, expected_updated_at: previous.updated_at } });
  expect(saved.status()).toBe(200);
  await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`);
  return path;
}

test("physical log reset requires confirmation and preserves saved data until explicit save", async ({ page }) => {
  const path = await openSavedReadingLog(page);
  const reset = page.getByRole("button", { name: "পড়ার হিসাব খালি করুন", exact: true });
  page.once("dialog", dialog => dialog.dismiss());
  await reset.click();
  await expect(page.getByLabel("বর্তমান পৃষ্ঠা", { exact: true })).toHaveValue("25");
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveValue(logValues.notes);
  page.once("dialog", dialog => dialog.accept());
  await reset.click();
  await expect(page.getByLabel("পড়ার অবস্থা", { exact: true })).toHaveValue("unread");
  await expect(page.getByLabel("বর্তমান পৃষ্ঠা", { exact: true })).toHaveValue("0");
  for (const label of ["মোট পৃষ্ঠা (ঐচ্ছিক)", "পড়া শুরুর তারিখ", "পড়া শেষের তারিখ", "পড়ার ব্যক্তিগত নোট"]) await expect(page.getByLabel(label, { exact: true })).toHaveValue("");
  await expect(page.getByLabel("আপনার মূল্যায়ন", { exact: true })).toHaveValue("0");
  const unchanged = await (await page.request.get(path)).json();
  expect(unchanged.notes).toBe(logValues.notes); expect(unchanged.current_page).toBe(25);
  await page.getByRole("button", { name: "পড়ার হিসাব সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "পড়ার হিসাব সংরক্ষিত হয়েছে।" })).toBeVisible();
  const cleared = await (await page.request.get(path)).json();
  expect(cleared).toMatchObject({ status: "unread", current_page: 0, total_pages: null, rating: 0, started_on: null, finished_on: null, notes: "" });
  await page.reload();
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveValue("");
  await setLanguage(page, "en");
  await expect(page.getByRole("button", { name: "Reset reading log", exact: true })).toBeVisible();
});

test("pending or conflicted physical-log writes block reset and retain the edited draft", async ({ page }) => {
  const path = await openSavedReadingLog(page);
  let writes = 0, release;
  const pending = new Promise(resolve => { release = resolve; });
  await page.route(`**${path}`, async route => {
    if (route.request().method() !== "PUT") return route.continue();
    writes += 1;
    await pending;
    await route.fulfill({ status: 409, json: { code: "state_conflict", detail: "The saved reading log changed.", field_errors: {} } });
  });
  await page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true }).fill("সংরক্ষণ না করা নোট");
  await page.getByRole("button", { name: "পড়ার হিসাব সংরক্ষণ করুন", exact: true }).click();
  await expect.poll(() => writes).toBe(1);
  const reset = page.getByRole("button", { name: "পড়ার হিসাব খালি করুন", exact: true });
  await expect(reset).toBeDisabled();
  release();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(reset).toBeDisabled();
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveValue("সংরক্ষণ না করা নোট");
  expect((await (await page.request.get(path)).json()).notes).toBe(logValues.notes);
  expect(writes).toBe(1);
});
