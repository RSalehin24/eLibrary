import { randomUUID } from "node:crypto";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("unfinished books expose changed contents, last check and a direct update action", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.goto(`/manage/unfinished/?status=updated&q=${encodeURIComponent(fixture.sources.query)}`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Unfinished Books", exact: true })).toBeVisible();
  const rows = page.locator(".source-row");
  await expect(rows).toHaveCount(1);
  await expect(rows.locator(".source-update-label")).toHaveText("Updates Available");
  await expect(rows.locator(".source-update small")).toContainText("Last Checked");
  await expect(rows.locator(".source-update small")).toContainText(/\d{1,2}:\d{2} [AP]M.*Dhaka/);
  await rows.getByRole("link", { name: "Update Book", exact: true }).click();
  await expect(page).toHaveURL(/\/manage\/books\/[^/]+\/$/);
  await expect(page.getByRole("heading", { level: 1, name: fixture.reading_book.title, exact: true })).toBeVisible();
});

test("queued source work explains automatic processing and keeps technical details collapsed", async ({ page }) => {
  await useAccount(page, "administrator");
  const { csrf_token: token } = await (await page.request.get("/api/v1/auth/session/")).json();
  const sources = await (await page.request.get(`/api/v1/manage/sources/?status=unlinked&q=${encodeURIComponent(fixture.sources.query)}`)).json();
  const source = sources.entries.find(entry => entry.can_process);
  expect(source).toBeTruthy();
  const response = await page.request.post(`/api/v1/manage/sources/${source.id}/process/`, { headers: { "X-CSRFToken": token }, data: { operation_id: randomUUID(), expected_updated_at: source.updated_at } });
  expect(response.status()).toBe(202);
  const operation = await response.json();
  await page.goto(`/manage/jobs/${operation.operation_id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Create Book from Website", exact: true })).toBeVisible();
  expect(await page.locator(".job-heading h2 a").evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(22);
  await expect(page.getByRole("heading", { name: "Processing Starts Automatically", exact: true })).toBeVisible();
  await expect(page.locator(".job-next-step p").filter({ hasText: "Books Queued Earlier:" })).toBeVisible();
  await expect(page.locator(".job-next-step strong")).toHaveText(/^\d[\d,]*$/);
  await expect(page.locator(".job-steps li")).toHaveCount(5);
  await expect(page.locator(".job-identifier")).toBeHidden();
  await page.getByText("Technical Details", { exact: true }).click();
  await expect(page.locator(".job-identifier")).toHaveText(operation.operation_id);
  await page.getByText("Technical Details", { exact: true }).click();
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(page.getByRole("heading", { name: "নিজে থেকেই কাজ শুরু হবে", exact: true })).toBeVisible();
  await expect(page.getByText("কারিগরি তথ্য", { exact: true })).toBeVisible();
  await expect(page.locator(".job-detail").getByText("সংগৃহীত পাতা: ০", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("unavailable source text shows an automatic recheck time without asking for manual approval", async ({ page }) => {
  await useAccount(page, "administrator");
  const path = `/api/v1/manage/jobs/${fixture.preparation_job.id}/`;
  const original = await (await page.request.get(path)).json();
  const job = { ...original, kind: "process_source", state: "retry_wait", error_code: "source_content_unavailable", available_at: "2026-10-18T07:45:00Z", queue_ahead: null, actions: [] };
  await page.route(`**${path}`, route => route.fulfill({ json: job }));
  await page.goto(`/manage/jobs/${fixture.preparation_job.id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.getByRole("button", { name: "Refresh Status", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Waiting for Source Text", exact: true })).toBeVisible();
  await expect(page.locator(".job-heading + p")).toContainText("Waiting for Source Text");
  await expect(page.locator(".job-next-step")).toContainText("1:45 PM (Dhaka)");
  await expect(page.locator(".job-next-step")).toContainText("automatically");
  await expect(page.locator(".source-issue-form")).toHaveCount(0);
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(page.getByRole("heading", { name: "ওয়েবসাইটে লেখা আসার অপেক্ষা", exact: true })).toBeVisible();
  expect(await page.locator(".job-next-step").innerText()).not.toMatch(/[A-Za-z0-9]/);
});

test("source layout filters preserve the real diagnostic view and both languages", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.goto("/manage/jobs/?kind=process_source&layout=multi_page");
  await page.getByRole("button", { name: "English", exact: true }).click();
  const layout = page.getByLabel("Contents and reading layout", { exact: true });
  await expect(layout).toHaveValue("multi_page");
  const searchButton = page.getByRole("search").getByRole("button", { name: "Search", exact: true });
  expect(await searchButton.evaluate(element => {
    const label = [...element.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent?.trim());
    if (!label) return false;
    const text = document.createRange(); text.selectNodeContents(label);
    return text.getClientRects().length === 1;
  })).toBe(true);
  await expect(layout.getByRole("option", { name: "Multi-page contents", exact: true })).toHaveCount(1);
  await layout.selectOption("complex");
  await page.getByRole("button", { name: "Apply Filters", exact: true }).click();
  await expect(page).toHaveURL(/layout=complex/);
  await expect(page.getByLabel("Job type", { exact: true })).toHaveValue("process_source");
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(page.getByLabel("সূচিপত্র ও লেখার ধরন", { exact: true })).toHaveValue("complex");
  await expect(page.getByRole("option", { name: "একাধিক পাতা বা স্তরের সূচিপত্র", exact: true })).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("source diagnostics show contents coverage and code-update recovery without a manual review gate", async ({ page }) => {
  await useAccount(page, "administrator");
  const path = `/api/v1/manage/jobs/${fixture.preparation_job.id}/`;
  const original = await (await page.request.get(path)).json();
  const fingerprint = "a".repeat(64);
  const job = { ...original, kind: "process_source", state: "failed", error_code: "source_export_content_mismatch", actions: [],
    source_layout: { structure_type: "lesson_topic_nested", multi_page: true, contents_pages: 5, collected_contents_pages: 3, contents_incomplete: true },
    source_defect: { fingerprint, code_version: "b".repeat(64), code_group: "export", error_code: "source_export_content_mismatch", stage: "generating_exports" } };
  await page.route(`**${path}`, route => route.fulfill({ json: job }));
  await page.route(`**${path}source-issue/`, route => route.fulfill({ json: { id: job.id, expected_updated_at: job.updated_at, title: "Source diagnostics", author_line: "", validation_status: "", error_count: 0, warning_count: 0, candidates: [], available_choices: ["cancel"], verification: null } }));
  await page.goto(`/manage/jobs/${fixture.preparation_job.id}/`);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.getByRole("button", { name: "Refresh Status", exact: true }).click();
  await expect(page.getByText("Contents pages collected: 3 / 5", { exact: true })).toBeVisible();
  await expect(page.getByText("Some contents pages are missing. The book stays unpublished until all reading text is collected.", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "View jobs with this defect", exact: true })).toHaveAttribute("href", `/manage/jobs/?q=${fingerprint}`);
  await expect(page.getByText("A processing defect was detected. This book will retry automatically after the relevant processing code is updated.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "বাংলা", exact: true }).click();
  await expect(page.getByText("সংগৃহীত সূচিপত্রের পাতা: ৩ / ৫", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "একই সমস্যার কাজগুলো দেখুন", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
