import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

async function cancelledDelivery(page) {
  const options = await (await page.request.get(`/api/v1/delivery/books/${encodeURIComponent(fixture.reading_book.slug)}/kindle/`)).json();
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const headers = { "X-CSRFToken": session.csrf_token };
  const accepted = await page.request.post(`/api/v1/delivery/books/${encodeURIComponent(fixture.reading_book.slug)}/kindle/`, { headers, data: { operation_id: randomUUID(), expected_updated_at: options.asset_revision, recipients: ["other@kindle.com"] } });
  expect(accepted.status()).toBe(202);
  const operation = await accepted.json();
  const detail = await (await page.request.get(operation.status_url)).json();
  expect((await page.request.post(operation.status_url, { headers, data: { expected_updated_at: detail.updated_at } })).status()).toBe(202);
  return operation.operation_id;
}

test("Kindle history combines filters and resend only prefills the previous recipient", async ({ page }) => {
  await useAccount(page, "kindle_reader");
  await page.setViewportSize({ width: 390, height: 844 });
  const identifier = await cancelledDelivery(page);
  await page.goto("/kindle/");
  await page.getByRole("button", { name: "English", exact: true }).click();
  const filters = page.getByRole("form", { name: "Search Kindle requests" });
  await filters.getByLabel("Book title or code", { exact: true }).fill(fixture.reading_book.title);
  await filters.getByLabel("Delivery status", { exact: true }).selectOption("cancelled");
  await filters.getByLabel("Sort Kindle requests", { exact: true }).selectOption("title");
  await filters.getByRole("button", { name: "Apply filters", exact: true }).click();
  await expect(page).toHaveURL(/state=cancelled/);
  await expect(page.getByLabel("Book title or code", { exact: true })).toHaveValue(fixture.reading_book.title);
  const card = page.locator(".job-card").filter({ has: page.locator(`a[href="/kindle/operations/${identifier}/"]`) });
  await expect(card).toContainText(fixture.reading_book.title);
  let submissions = 0;
  page.on("request", (request) => { if (request.method() === "POST" && request.url().includes("/delivery/books/")) submissions += 1; });
  await card.getByRole("link", { name: "Send again", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`resend=${identifier}`));
  await expect(page.getByRole("checkbox", { name: "other@kindle.com", exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "reader@kindle.com", exact: true })).not.toBeChecked();
  await expect(page.getByText("Previously used addresses that remain in your profile are selected. Confirm your selection before sending.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Request Book Delivery", exact: true })).toBeEnabled();
  expect(submissions).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/kindle-resend-390.png", fullPage: true });
  await useAccount(page, "reader");
  expect((await page.request.get(`/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/?resend=${identifier}`)).status()).toBe(200);
  await page.goto(`/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/?resend=${identifier}`);
  await expect(page.getByRole("checkbox")).toHaveCount(0);
});

test("invalid Kindle filters fail clearly and a cancelled request cannot point at another book", async ({ page }) => {
  await useAccount(page, "kindle_reader");
  for (const query of ["sort=__proto__", "state=unknown", "from_date=bad", "q=a&q=b", "from_date=2026-10-20&to_date=2026-10-18"]) {
    expect((await page.request.get(`/kindle/?${query}`)).status()).toBe(404);
  }
  const identifier = await cancelledDelivery(page);
  await useAccount(page, "administrator");
  expect((await page.request.get(`/kindle/books/${encodeURIComponent(fixture.reading_book.slug)}/?resend=${identifier}`)).status()).toBe(404);
});
