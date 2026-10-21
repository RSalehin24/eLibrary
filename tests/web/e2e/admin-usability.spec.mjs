import { test, expect, useAccount, setLanguage } from "./fixtures.mjs";
import { useIdleDiscoveryOptions } from "./source-console-fixture.mjs";

const revision = "2026-10-17T00:00:00Z";
const entries = [
  { id: "2de0123b-9524-416a-8305-799bb306c6ea", title: "পথের পাঁচালী", author_line: "বিভূতিভূষণ বন্দ্যোপাধ্যায়", can_process: true },
  { id: "33f3e162-8125-4e68-bf37-850508d33bc5", title: "দেবদাস", author_line: "শরৎচন্দ্র চট্টোপাধ্যায়", can_process: true },
  { id: "441fb588-a7c2-4558-85f4-3d1acacbc42c", title: "Unavailable source", author_line: "", can_process: false },
].map((entry) => ({ ...entry, source_url: null, created_at: revision, last_seen_at: revision, updated_at: revision,
  book: null, can_edit_book: false, active_operation_id: null, latest_operation_id: null }));

async function openCatalog(page) {
  await useAccount(page, "administrator");
  await page.route("**/api/v1/**", (route) => route.request().method() === "GET" ? route.continue() : route.abort());
  await useIdleDiscoveryOptions(page);
  await page.route("**/api/v1/manage/sources/?*", (route) => route.fulfill({ json: { entries, pagination: { page: 1, limit: 50, total_count: 3 } } }));
  await page.goto("/manage/sources/?q=admin-usability-review");
  await setLanguage(page, "en");
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".source-row")).toHaveCount(3);
  await page.locator(".source-advanced > summary").click();
}

function results(command) {
  return { entries: command.entries.map((entry) => ({ source_id: entry.source_id, operation_id: entry.operation_id, accepted: true, error: null })) };
}

test("language switching preserves entered fields and persists across navigation and reload", async ({ page }) => {
  page.on("dialog", (dialog) => dialog.accept());
  await openCatalog(page);
  await expect(page.getByRole("heading", { name: "Book Creation", exact: true, level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: entries[0].title, exact: true })).toBeVisible();
  await page.getByLabel("Maximum Pages", { exact: true }).fill("3");
  await page.getByRole("checkbox", { name: `${entries[0].title} — Select`, exact: true }).check();
  await setLanguage(page, "bn");
  await expect(page.getByRole("heading", { name: "বই তৈরি", exact: true, level: 1 })).toBeVisible();
  await expect(page.getByLabel("সর্বোচ্চ পাতা", { exact: true })).toHaveValue("3");
  await expect(page.getByRole("checkbox", { name: `${entries[0].title} — নির্বাচন করুন`, exact: true })).toBeChecked();
  await setLanguage(page, "en");
  await page.getByRole("button", { name: "Clear Selection", exact: true }).click();
  await page.goto("/manage/books/new/");
  await page.getByLabel("Book Title", { exact: true }).fill("A draft that must survive switching");
  await setLanguage(page, "bn");
  await expect(page.getByLabel("বইয়ের নাম", { exact: true })).toHaveValue("A draft that must survive switching");
  await setLanguage(page, "en");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Add Book", exact: true })).toBeVisible();
  await expect(page.locator(".management-workspace")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("button", { name: "English", exact: true })).toHaveAttribute("aria-pressed", "true");
});

test("select all excludes unavailable sources and partial results preserve only rejected books", async ({ page }) => {
  await openCatalog(page); let command;
  await page.route("**/api/v1/manage/sources/process-selection/", async (route) => {
    command = route.request().postDataJSON(); const response = results(command);
    response.entries[0] = { ...response.entries[0], accepted: false, error: { code: "state_conflict", detail: "This book changed.", field_errors: {} } };
    await route.fulfill({ json: response });
  });
  const all = page.getByRole("checkbox", { name: "Select all available books on this page", exact: true });
  await all.check(); await expect(page.locator(".source-row input:checked")).toHaveCount(2);
  await expect(page.getByRole("checkbox", { name: "Unavailable source — Select", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Create Selected Books", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Books that were not accepted remain selected." })).toBeVisible();
  expect(command.entries).toHaveLength(2);
  expect(command.entries.every((entry) => entry.expected_updated_at === revision)).toBe(true);
  expect(new Set(command.entries.map((entry) => entry.operation_id)).size).toBe(2);
  await expect(page.locator(".source-row input:checked")).toHaveCount(1);
  await expect(page.getByRole("checkbox", { name: `${entries[0].title} — Select`, exact: true })).toBeChecked();
  await expect(page.getByRole("link", { name: "View Job", exact: true })).toHaveCount(1);
  expect(await all.evaluate((element) => element.indeterminate)).toBe(true);
  await page.getByRole("button", { name: "Clear Selection", exact: true }).click();
  await expect(page.locator(".source-row input:checked")).toHaveCount(0);
  const fullPage = Array.from({ length: 100 }, (_, index) => ({ ...entries[0], id: crypto.randomUUID(), title: `Limit book ${index}` }));
  await page.route("**/api/v1/manage/sources/?*", (route) => route.fulfill({ json: { entries: fullPage, pagination: { page: 1, limit: 100, total_count: 100 } } }));
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".source-row")).toHaveCount(100); await all.check();
  await expect(page.locator(".source-row input:checked")).toHaveCount(100);
  await page.route("**/api/v1/manage/sources/?*", (route) => route.fulfill({ json: { entries: [entries[1]], pagination: { page: 1, limit: 50, total_count: 1 } } }));
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".source-row")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Create Book", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Clear Selection", exact: true }).click();
  await expect(page.getByRole("button", { name: "Create Book", exact: true })).toBeEnabled();
});

test("a row creates one revision-pinned job and disables repeat submission while pending", async ({ page }) => {
  await openCatalog(page); let command, writes = 0, release;
  const pending = new Promise((resolve) => { release = resolve; });
  await page.route("**/api/v1/manage/sources/process-selection/", async (route) => {
    writes += 1; command = route.request().postDataJSON(); await pending; await route.fulfill({ json: results(command) });
  });
  await page.locator(".source-row").filter({ hasText: entries[0].title }).getByRole("button", { name: "Create Book", exact: true }).click();
  await expect.poll(() => writes).toBe(1);
  await expect(page.getByRole("button", { name: "Create Selected Books", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Create Book", exact: true }).first()).toBeDisabled();
  expect(command.entries).toHaveLength(1); expect(command.entries[0].source_id).toBe(entries[0].id);
  expect(command.entries[0].expected_updated_at).toBe(revision);
  release(); await expect(page.getByRole("link", { name: "View Job", exact: true })).toHaveCount(1);
  await expect(page.getByRole("status").filter({ hasText: "Book creation has been queued." })).toBeVisible();
  expect(writes).toBe(1);
});

test("a lost response prevents replay and exposes the original operation link", async ({ page }) => {
  await openCatalog(page); let command, writes = 0;
  await page.route("**/api/v1/manage/sources/process-selection/", async (route) => {
    writes += 1; command = route.request().postDataJSON(); await route.abort("failed");
  });
  await page.locator(".source-row").filter({ hasText: entries[1].title }).getByRole("button", { name: "Create Book", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "The result is uncertain" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Selected Books", exact: true })).toBeDisabled();
  await expect(page.locator(`a[href="/manage/jobs/${command.entries[0].operation_id}/"]`)).toBeVisible();
  await setLanguage(page, "bn");
  await expect(page.getByRole("button", { name: "নির্বাচিত বই তৈরি করুন", exact: true })).toBeDisabled(); expect(writes).toBe(1);
});

test("phone catalog keeps selection controls usable at 200 percent text in both languages", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 }); await openCatalog(page);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  await page.getByRole("checkbox", { name: "Select all available books on this page", exact: true }).check();
  for (const language of ["English", "বাংলা"]) {
    await setLanguage(page, language === "English" ? "en" : "bn");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await expect(page.locator(".source-row input:checked")).toHaveCount(2);
  }
  await page.screenshot({ path: "test-artifacts/foundation/admin-usability-320.png", fullPage: true });
});

test("English preference covers the main admin pages, forms and status filters", async ({ page }) => {
  await openCatalog(page);
  for (const [path, heading] of [
    ["/manage/", "Book Creation"], ["/manage/books/", "All Books"], ["/manage/books/new/", "Add Book"],
    ["/manage/entities/", "Authors & Contributors"],
    ["/manage/entities/contributors/new/", /Add Entry/], ["/manage/automations/", "Schedules"],
    ["/manage/automations/new/", "New Schedule"], ["/manage/users-access/", "Users"],
    ["/manage/users-access/invite/", "Invite Reader"], ["/manage/jobs/", "Processing"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, exact: typeof heading === "string", level: 1 })).toBeVisible();
    const controls = await page.locator('.management-workspace label, .management-workspace button:not([lang="bn"]), .management-workspace select option').evaluateAll(elements => elements.map(element => {
      const copy = element.cloneNode(true);
      copy.querySelectorAll('[translate="no"]').forEach(content => content.remove());
      return copy.textContent;
    }));
    expect(controls.filter((text) => /[\u0980-\u09ff]/u.test(text))).toEqual([]);
    const jobSelections = page.locator('.job-card .selection-toggle');
    for (const label of await jobSelections.all()) {
      await expect(label.locator('[translate="no"]')).not.toBeEmpty();
      expect((await label.textContent()).trim()).toMatch(/^Select:/);
    }
    await expect(page.getByRole("alert").filter({ hasText: /failed|পাওয়া যায়নি/i })).toHaveCount(0);
  }
});

test("phone navigation stays visible and all primary workflow actions remain above the fold", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await openCatalog(page);
  await page.getByRole("button", { name: "Open menu", exact:true }).click();
  await expect(page.locator(".admin-navigation-drawer .workspace-nav a")).toHaveCount(6);
  await page.keyboard.press("Escape");
  const row = page.locator(".source-row").first(), selection = row.locator("label");
  const target = await selection.boundingBox();
  expect(target.width).toBeGreaterThanOrEqual(44); expect(target.height).toBeGreaterThanOrEqual(44);
  await selection.click({ position: { x: 5, y: 5 } }); await expect(row.getByRole("checkbox")).toBeChecked();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  for (const name of ["Fetch All", "Process All", "Schedule Automation"]) {
    const action = await page.getByRole("button", { name, exact: true }).boundingBox();
    expect(action.y + action.height).toBeLessThan(844);
  }
  await setLanguage(page, "bn");
  await page.getByRole("button", { name: "মেনু খুলুন", exact:true }).click();
  await expect(page.locator('.admin-navigation-drawer .workspace-nav a[aria-current="page"]')).toBeVisible();
});
