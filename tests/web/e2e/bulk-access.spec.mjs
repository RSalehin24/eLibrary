import { test, expect, fixture, useAccount } from "./fixtures.mjs";
import { randomUUID } from "node:crypto";

async function createBulkAccount(page) {
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": session.csrf_token };
  const response = await page.request.post("/api/v1/manage/invitations/", { headers, data: { operation_id: randomUUID(), email: `bulk-browser-${randomUUID()}@example.test`, full_name: "Bulk permissions browser check" } });
  expect(response.status()).toBe(202);
  const operation = await response.json();
  const job = await (await page.request.get(operation.status_url)).json();
  expect((await page.request.post(operation.status_url, { headers, data: { action: "cancel", expected_updated_at: job.updated_at } })).status()).toBe(202);
  return job.account_id;
}

test("bulk permissions retain selections across search and report every item on a phone", async ({ page }) => {
  await useAccount(page, "access_manager");
  await page.setViewportSize({ width: 390, height: 844 });
  const account = await createBulkAccount(page);
  await page.goto(`/manage/users-access/${account}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  const form = page.locator("form.bulk-access");
  await expect(form.getByRole("heading", { name: "Grant multiple permissions" })).toBeVisible();
  const search = form.getByLabel("Search targets for bulk access");
  const selected = [fixture.reading_book, fixture.update_book];
  for (const book of selected) {
    await search.fill(book.title);
    await form.getByRole("checkbox", { name: book.title, exact: true }).check();
  }
  await expect(form.locator(".bulk-access-selected li")).toHaveCount(2);
  await form.getByRole("checkbox", { name: "Download Book", exact: true }).check();
  await form.getByRole("checkbox", { name: "Read Once", exact: true }).check();
  await expect(form.getByRole("checkbox", { name: "Reading Access", exact: true })).not.toBeChecked();
  await form.getByRole("checkbox", { name: "Reading Access", exact: true }).check();
  await form.getByLabel("Date", { exact: true }).fill("2027-11-20");
  const time = form.getByRole("group", { name: "Time", exact: true });
  await time.getByRole("combobox", { name: "hours", exact: true }).selectOption("3");
  await time.getByRole("combobox", { name: "minutes", exact: true }).selectOption("30");
  await time.getByRole("combobox", { name: "AM or PM", exact: true }).selectOption("PM");
  const writes = [];
  page.on("request", (request) => { if (request.method() === "POST" && request.url().endsWith("/grants/bulk/")) writes.push(request.postDataJSON()); });
  await form.getByRole("button", { name: "Grant selected permissions", exact: true }).click();
  const result = form.getByRole("region", { name: "Permission results", exact: true });
  await expect(result.locator("li")).toHaveCount(4);
  expect(writes).toHaveLength(1);
  expect(writes[0].entries).toHaveLength(4);
  expect(new Set(writes[0].entries.map((entry) => entry.id)).size).toBe(4);
  expect(writes[0].entries.every((entry) => entry.expires_at === "2027-11-20T09:30:00.000Z")).toBe(true);
  await expect(result.getByRole("status")).toContainText("Created: 4");
  const replay = page.waitForResponse((response) => response.url().endsWith("/grants/bulk/") && response.request().method() === "POST");
  await form.getByRole("button", { name: "Grant selected permissions", exact: true }).click();
  await replay;
  await expect(result.getByRole("status")).toContainText("Created: 0");
  expect(writes[1]).toEqual(writes[0]);
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(form.getByRole("heading", { name: "একসঙ্গে একাধিক অনুমতি দিন" })).toBeVisible();
  await expect(form.getByRole("status")).toContainText("যোগ হয়েছে:");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("uncertain bulk response keeps selections and prevents an automatic resend", async ({ page }) => {
  await useAccount(page, "access_manager");
  await page.goto(`/manage/users-access/${fixture.access_conflict_reader.id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  const form = page.locator("form.bulk-access");
  await form.getByLabel("Bulk permission target", { exact: true }).selectOption("account");
  let writes = 0;
  await page.route("**/api/v1/manage/users/*/grants/bulk/", async (route) => {
    writes += 1;
    await route.fulfill({ status: 503, json: { code: "unavailable", detail: "Synthetic unavailable result", field_errors: {} } });
  });
  await form.getByRole("button", { name: "Grant selected permissions", exact: true }).click();
  await expect(form.getByRole("alert")).toContainText("The result is uncertain");
  await expect(form.getByRole("button", { name: "Grant selected permissions", exact: true })).toBeDisabled();
  await expect(form.getByLabel("Bulk permission target", { exact: true })).toHaveValue("account");
  await expect(form.getByRole("checkbox", { name: "Reading Access", exact: true })).toBeChecked();
  expect(writes).toBe(1);
});
