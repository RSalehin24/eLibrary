import { test, expect, fixture, useAccount, setLanguage } from "./fixtures.mjs";

test("linked contributor and category forms explain administrator authority in both languages", async ({ page }) => {
  await useAccount(page, "administrator");
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const path = `/api/v1/manage/books/${encodeURIComponent(fixture.book.slug)}/relationships/`;
  const relationships = await (await page.request.get(path)).json();
  const saved = await page.request.patch(path, {
    headers: { "X-CSRFToken": session.csrf_token },
    data: { expected_updated_at: relationships.updated_at,
      contributors: [{ id: fixture.entities.contributor.id, role: "author" }],
      category_ids: [fixture.entities.category.id] },
  });
  expect(saved.status()).toBe(200);
  await useAccount(page, "editor");
  for (const [kind, entity] of [["contributors", fixture.entities.contributor], ["categories", fixture.entities.category]]) {
    await page.goto(`/manage/entities/${kind}/${entity.id}/`);
    await expect(page.getByRole("heading", { name: entity.name, exact: true })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "পরিবর্তন করতে প্রশাসকের অনুমতি প্রয়োজন" })).toBeVisible();
    await expect(page.locator(".editorial-form")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "পরিবর্তন সংরক্ষণ করুন", exact: true })).toHaveCount(0);
    await setLanguage(page, "en");
    await expect(page.getByRole("status").filter({ hasText: "Administrator permission is required to edit it" })).toBeVisible();
    await setLanguage(page, "bn");
  }
  await useAccount(page, "administrator");
  await page.goto(`/manage/entities/contributors/${fixture.entities.contributor.id}/`);
  await expect(page.getByLabel("নাম", { exact: true })).toBeEnabled();
});
