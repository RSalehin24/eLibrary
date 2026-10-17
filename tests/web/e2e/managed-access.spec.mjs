import { test, expect, fixture, useAccount } from "./fixtures.mjs";

const accountPath = (account) => `/manage/users-access/${fixture[account].id}/`;

test("user management is private and hidden from reader and metadata accounts", async ({ page }) => {
  await useAccount(page, "reader"); await page.goto("/my-books/");
  await expect(page.locator(".workspace-nav").getByRole("link", { name: "ব্যবহারকারী ও অনুমতি", exact: true })).toHaveCount(0);
  expect((await page.request.get("/manage/users-access/")).status()).toBe(404);
  expect((await page.request.get("/api/v1/manage/users/")).status()).toBe(403);
  await useAccount(page, "editor"); expect((await page.request.get(accountPath("managed_reader"))).status()).toBe(404);
  await useAccount(page, "access_manager"); await page.goto(`/manage/users-access/?q=${encodeURIComponent(fixture.managed_reader.email)}`);
  await expect(page.getByRole("link", { name: "Foundation managed-reader", exact: true })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  for (const query of ["page=0", "page=1e2", "page=999999999", "page=1&page=2", "status=__proto__"]) expect((await page.request.get(`/manage/users-access/?${query}`)).status()).toBe(404);
});

test("phone access workflow saves accounts and manages a scoped grant without transferring ownership", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(accountPath("managed_reader"));
  await page.getByLabel("পাঠকের নাম", { exact: true }).fill("অনুমতির পরীক্ষার পাঠক");
  await page.getByRole("button", { name: "অ্যাকাউন্ট সংরক্ষণ করুন", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "অ্যাকাউন্টের পরিবর্তন সংরক্ষিত হয়েছে" })).toBeVisible();
  await page.getByLabel("অনুমতির পরিধি", { exact: true }).selectOption("book");
  await page.getByLabel("বই, বিভাগ বা লেখকের নাম খুঁজুন").fill(fixture.reading_book.title);
  await expect(page.getByLabel("বই, বিভাগ বা লেখক বেছে নিন")).toBeEnabled();
  await page.getByLabel("বই, বিভাগ বা লেখক বেছে নিন").selectOption(fixture.reading_book.id);
  const save = page.getByRole("button", { name: "অনুমতি যোগ করুন", exact: true });
  expect((await save.boundingBox()).height).toBeGreaterThanOrEqual(44);
  await save.click(); const card = page.locator("[data-grant-id]");
  await expect(card).toContainText("কার্যকর"); await expect(card).toContainText(fixture.reading_book.title);
  await card.locator("summary").click(); await card.getByLabel("মন্তব্য", { exact: true }).fill("নির্দিষ্ট বইয়ের পাঠ" );
  await expect(card.getByRole("button", { name: "অনুমতি প্রত্যাহার করুন" })).toBeDisabled();
  await card.getByRole("button", { name: "অনুমতির তথ্য সংরক্ষণ করুন", exact: true }).click();
  await expect(card.getByRole("button", { name: "অনুমতি প্রত্যাহার করুন" })).toBeEnabled();
  await page.reload(); await card.locator("summary").click(); await expect(card.getByLabel("মন্তব্য", { exact: true })).toHaveValue("নির্দিষ্ট বইয়ের পাঠ");
  await card.getByRole("button", { name: "অনুমতি প্রত্যাহার করুন", exact: true }).click(); await expect(card).toContainText("প্রত্যাহৃত");
  await card.getByRole("button", { name: "অনুমতি ফিরিয়ে দিন", exact: true }).click(); await expect(card).toContainText("কার্যকর");
  await useAccount(page, "managed_reader");
  const access = await page.request.get(`/api/v1/reading/books/${encodeURIComponent(fixture.reading_book.slug)}/access/`);
  expect(access.status()).toBe(200); expect((await access.json()).can_read).toBe(true);
  const library = await page.request.get("/api/v1/me/books/"); expect((await library.json()).entries).toHaveLength(0);
});

test("stale account edits preserve the draft and never automatically replay", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto(accountPath("access_conflict_reader"));
  const name = page.getByLabel("পাঠকের নাম", { exact: true }); await name.fill("অসম্পূর্ণ লেখা রাখা হবে");
  const response = await page.request.get(`/api/v1/manage/users/${fixture.access_conflict_reader.id}/`), current = await response.json();
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  expect((await page.request.patch(`/api/v1/manage/users/${current.id}/`, { data: { expected_updated_at: current.updated_at, full_name: "অন্য জায়গায় পরিবর্তন" }, headers: { "X-CSRFToken": session.csrf_token } })).status()).toBe(200);
  await page.getByRole("button", { name: "অনুমতি যোগ করুন", exact: true }).click();
  await expect(page.getByText("অনুমতি সংরক্ষিত হয়েছে।", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "অন্য জায়গায় পরিবর্তন", exact: true })).toBeVisible();
  const writes = []; page.on("request", (request) => { if (request.method() === "PATCH") writes.push(request); });
  await page.getByRole("button", { name: "অ্যাকাউন্ট সংরক্ষণ করুন", exact: true }).click();
  await expect(page.locator(".account-settings").getByRole("alert")).toContainText("তথ্যটি অন্য জায়গায় বদলেছে");
  await expect(name).toHaveValue("অসম্পূর্ণ লেখা রাখা হবে");
  await expect(page.getByRole("button", { name: "অ্যাকাউন্ট সংরক্ষণ করুন", exact: true })).toBeDisabled(); expect(writes).toHaveLength(1);
});

test("uncertain grant writes stop resubmission and keep the selected scope", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto(accountPath("access_conflict_reader"));
  await page.getByLabel("যে কাজের অনুমতি", { exact: true }).selectOption("send:kindle");
  const writes = [];
  await page.route("**/api/v1/manage/users/*/grants/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    writes.push(route.request().postDataJSON()); await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "unavailable", detail: "Synthetic uncertain write", field_errors: {} }) });
  });
  await page.getByRole("button", { name: "অনুমতি যোগ করুন", exact: true }).click();
  await expect(page.locator(".account-settings").getByRole("alert")).toContainText("ফলাফল নিশ্চিত করা যায়নি");
  await expect(page.getByRole("button", { name: "অনুমতি যোগ করুন", exact: true })).toBeDisabled();
  await expect(page.getByLabel("যে কাজের অনুমতি", { exact: true })).toHaveValue("send:kindle"); expect(writes).toHaveLength(1);
});

test("self and staff account details have no management forms", async ({ page }) => {
  await useAccount(page, "access_manager");
  for (const account of ["access_manager", "administrator"]) {
    await page.goto(accountPath(account)); await expect(page.getByRole("button", { name: "অ্যাকাউন্ট সংরক্ষণ করুন", exact: true })).toHaveCount(0);
    await expect(page.getByText("নিজের বা সুরক্ষিত অ্যাডমিন অ্যাকাউন্ট এখানে বদলানো যাবে না।")).toBeVisible();
  }
});

test("target search cancels obsolete reads and never applies their results", async ({ page }) => {
  await useAccount(page, "access_manager"); await page.goto(accountPath("managed_reader"));
  await page.getByLabel("অনুমতির পরিধি", { exact: true }).selectOption("book");
  let release; const held = new Promise((resolve) => { release = resolve; }); const queries = [];
  await page.route("**/api/v1/manage/access/references/**", async (route) => {
    const query = new URL(route.request().url()).searchParams.get("q"); queries.push(query);
    if (query === fixture.reading_book.title) await held;
    await route.continue();
  });
  const search = page.getByLabel("বই, বিভাগ বা লেখকের নাম খুঁজুন");
  await search.fill(fixture.reading_book.title); await expect.poll(() => queries.includes(fixture.reading_book.title)).toBe(true);
  await search.fill(fixture.update_book.title);
  await expect(page.getByLabel("বই, বিভাগ বা লেখক বেছে নিন")).toBeDisabled();
  await expect(page.locator(`option[value="${fixture.update_book.id}"]`)).toHaveCount(1);
  release(); await expect(page.getByLabel("বই, বিভাগ বা লেখক বেছে নিন")).toBeEnabled();
  await expect(page.locator(`option[value="${fixture.reading_book.id}"]`)).toHaveCount(0);
  await expect(page.getByLabel("বই, বিভাগ বা লেখক বেছে নিন")).toHaveValue("");
});
