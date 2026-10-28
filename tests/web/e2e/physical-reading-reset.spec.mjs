import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("removed physical logs cannot be read or reset by either account", async ({ page }) => {
  for (const account of ["personal_reader", "administrator"]) {
    await useAccount(page, account);
    const path = `/api/v1/me/books/${encodeURIComponent(fixture.personal.paper.slug)}/physical-log/`;
    const session = await (await page.request.get("/api/v1/auth/session/")).json();
    expect((await page.request.get(path)).status()).toBe(404);
    const response = await page.request.put(path, {
      headers: { "X-CSRFToken": session.csrf_token },
      data: { status: "reading", current_page: 25, notes: "Removed log must not persist" },
    });
    expect(response.status()).toBe(404);
  }
});

test("personal book pages have no physical log controls", async ({ page }) => {
  await useAccount(page, "personal_reader");
  await page.goto(`/my-books/${encodeURIComponent(fixture.personal.paper.slug)}/`);
  await expect(page.getByRole("heading", { name: fixture.personal.paper.title, exact: true })).toBeVisible();
  for (const label of ["পড়ার হিসাব খালি করুন", "পড়ার হিসাব সংরক্ষণ করুন"]) {
    await expect(page.getByRole("button", { name: label, exact: true })).toHaveCount(0);
  }
  await expect(page.getByLabel("পড়ার ব্যক্তিগত নোট", { exact: true })).toHaveCount(0);
});
