import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";
import { newDigitalBook } from "./book-fixture.mjs";

async function openBook(page, book) {
  await useAccount(page, "administrator");
  await page.goto(`/manage/books/${encodeURIComponent(book.slug)}/`);
  await setLanguage(page, "en");
  await expect(page.locator(".book-lifecycle-controls").getByRole("button", { name: "Remove Book", exact: true })).toBeEnabled();
}

async function simulatedRegeneration(page, book, status) {
  await page.route(`**/api/v1/manage/books/${encodeURIComponent(book.slug)}/controls/`, route => route.fulfill({ json: { book_revision: book.updated_at, can_regenerate: true, can_remove: true, regeneration_problem: null, active_operation_id: null } }));
  let operation, writes = 0;
  await page.route(`**/api/v1/manage/books/${encodeURIComponent(book.slug)}/regenerate/`, async route => {
    writes += 1; operation = route.request().postDataJSON().operation_id;
    await route.fulfill({ status, json: { code: status === 409 ? "state_conflict" : "unavailable", detail: "Synthetic command response", field_errors: {} } });
  });
  return () => ({ operation, writes });
}

test("book actions are visible in both languages, confirmations restore focus and drafts block commands", async ({ page }, info) => {
  const book = fixture.lifecycle_books[info.project.name];
  await openBook(page, book);
  const controls = page.locator(".book-lifecycle-controls");
  const regenerate = controls.getByRole("button", { name: "Regenerate Book", exact: true });
  await expect(regenerate).toBeEnabled();
  await regenerate.click();
  await expect(page.getByRole("dialog", { name: "Regenerate This Book?", exact: true })).toContainText("Previous files and reader notes");
  await page.keyboard.press("Escape"); await expect(regenerate).toBeFocused();
  await setLanguage(page, "bn");
  await expect(controls.getByRole("button", { name: "বই আবার তৈরি করুন", exact: true })).toBeEnabled();
  await expect(controls.getByRole("button", { name: "বই সরান", exact: true })).toBeEnabled();
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill("একটি অসম্পূর্ণ নাম");
  await expect(controls.getByRole("button", { name: "বই আবার তৈরি করুন", exact: true })).toBeDisabled();
  await expect(controls.getByRole("button", { name: "বই সরান", exact: true })).toBeDisabled();
  await page.getByLabel("বইয়ের নাম", { exact: true }).fill(book.title);
  await page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true }).click();
  await expect(controls.getByRole("button", { name: "বই আবার তৈরি করুন", exact: true })).toBeEnabled();
  await expect(controls.getByRole("button", { name: "বই সরান", exact: true })).toBeEnabled();
});

test("regeneration queues one real source operation and exposes its progress without repeating creation", async ({ page }, info) => {
  const book = fixture.lifecycle_books[info.project.name];
  await openBook(page, book);
  await page.getByRole("button", { name: "Regenerate Book", exact: true }).click();
  const accepted = page.waitForResponse(response => response.url().endsWith("/regenerate/") && response.status() === 202);
  await page.getByRole("button", { name: "Start Regeneration", exact: true }).click();
  const command = await (await accepted).json();
  await expect(page.locator(".book-lifecycle-controls").getByRole("link", { name: "View Job Status", exact: true })).toHaveAttribute("href", `/manage/jobs/${command.operation_id}/`);
  await expect(page.getByRole("button", { name: "Regenerate Book", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Remove Book", exact: true })).toBeDisabled();
  await page.locator(".book-lifecycle-controls").getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: book.title, exact: true })).toBeVisible();
  await expect(page.locator(".status-label")).toContainText("Queued");
});

test("uncertain regeneration retains its original operation and blocks another submission", async ({ page }) => {
  const book = await newDigitalBook(page), command = await simulatedRegeneration(page, book, 503);
  await openBook(page, book);
  await page.getByRole("button", { name: "Regenerate Book", exact: true }).click();
  await page.getByRole("button", { name: "Start Regeneration", exact: true }).click();
  const controls = page.locator(".book-lifecycle-controls");
  await expect(controls.getByRole("alert")).toBeVisible();
  await expect(controls.getByRole("link", { name: "Check Request Result", exact: true })).toHaveAttribute("href", `/manage/jobs/${command().operation}/`);
  await expect(page.getByRole("button", { name: "Regenerate Book", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Remove Book", exact: true })).toBeDisabled();
  expect(command().writes).toBe(1);
});

test("a stale regeneration decision preserves the metadata form and is not replayed", async ({ page }) => {
  const book = await newDigitalBook(page), command = await simulatedRegeneration(page, book, 409);
  await openBook(page, book);
  await page.getByRole("button", { name: "Regenerate Book", exact: true }).click();
  await page.getByRole("button", { name: "Start Regeneration", exact: true }).click();
  await expect(page.locator(".book-lifecycle-controls").getByRole("alert")).toBeVisible();
  await page.getByLabel("Book Title", { exact: true }).fill("A draft after a conflict");
  await setLanguage(page, "bn");
  await expect(page.getByLabel("বইয়ের নাম", { exact: true })).toHaveValue("A draft after a conflict");
  expect(command().writes).toBe(1);
});

test("removal requires confirmation, returns to the catalog and keeps enlarged phone layouts usable", async ({ page }) => {
  const book = await newDigitalBook(page);
  await openBook(page, book); await page.setViewportSize({ width: 320, height: 900 });
  await page.addStyleTag({ content: "html { font-size:200%; }" });
  const remove = page.getByRole("button", { name: "Remove Book", exact: true });
  await remove.click(); await expect(page.getByRole("dialog", { name: "Remove This Book?", exact: true })).toBeVisible();
  await page.keyboard.press("Escape"); await expect(remove).toBeFocused();
  expect((await page.request.get(`/api/v1/manage/books/${encodeURIComponent(book.slug)}/`)).status()).toBe(200);
  await remove.click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const close = page.getByRole("dialog").getByRole("button", { name: "Close", exact: true });
  expect(await close.evaluate(element => { const text = document.createRange(); text.selectNodeContents(element); return text.getClientRects().length; })).toBe(1);
  await page.screenshot({ path: `test-artifacts/foundation/lifecycle-removal-${test.info().project.name}.png` });
  const removed = page.waitForResponse(response => response.url().endsWith(`/manage/books/${encodeURIComponent(book.slug)}/`) && response.request().method() === "DELETE");
  await page.getByRole("button", { name: "Yes, Remove Book", exact: true }).click();
  expect((await removed).status()).toBe(204);
  await expect(page).toHaveURL(/\/manage\/books\/$/);
  expect((await page.request.get(`/api/v1/manage/books/${encodeURIComponent(book.slug)}/`)).status()).toBe(404);
});
