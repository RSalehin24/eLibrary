import { readFile } from "node:fs/promises";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("catalog exports include the applied search and print the entire filtered list in another tab", async ({ page, context }) => {
  await page.goto(`/catalog/?q=${encodeURIComponent(fixture.query)}`);
  const controls = page.getByRole("region", { name: "বইয়ের তালিকা ডাউনলোড", exact: true });
  await expect(controls.getByRole("button", { name: "CSV", exact: true })).not.toBeVisible();
  await controls.locator("summary").click();
  const downloadEvent = page.waitForEvent("download");
  await controls.getByRole("button", { name: "CSV", exact: true }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe("books.csv");
  const csv = await readFile(await download.path(), "utf8");
  expect(csv).toContain(fixture.book.title);
  expect(csv).not.toContain(fixture.editorial_book.title);
  const printEvent = context.waitForEvent("page");
  await controls.getByRole("link", { name: "প্রিন্ট / PDF হিসেবে সংরক্ষণ", exact: true }).click();
  const print = await printEvent;
  await print.waitForLoadState();
  expect(new URL(print.url()).searchParams.get("q")).toBe(fixture.query);
  await expect(print.getByText(fixture.book.title, { exact: true })).toBeVisible();
  await expect(print.locator(".instructions")).toContainText("Save as PDF");
  await print.close();
});

test("removed physical inventory has no export while unified catalog exports remain usable on a phone", async ({ page }) => {
  await useAccount(page, "administrator"); await page.setViewportSize({ width: 320, height: 800 });
  expect((await page.goto("/physical-books/?binding=hard_cover")).status()).toBe(404);
  expect((await page.request.get("/api/v1/physical-books/export/?export_format=xlsx")).status()).toBe(404);
  await page.goto(`/catalog/?q=${encodeURIComponent(fixture.personal.paper.title)}`);
  await expect(page.getByRole("heading", { name: fixture.personal.paper.title, exact: true })).toBeVisible();
  const controls = page.getByRole("region", { name: "বইয়ের তালিকা ডাউনলোড", exact: true });
  await controls.locator("summary").click();
  await expect(controls.getByRole("button", { name: "XLSX", exact: true })).toHaveCount(0);
  const downloading = page.waitForEvent("download");
  await controls.getByRole("button", { name: "CSV", exact: true }).click();
  const download = await downloading, csv = await readFile(await download.path(), "utf8");
  expect(csv).toContain(fixture.personal.paper.title);
  expect(csv).not.toMatch(/Record Type|Binding|Price/);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/unified-catalog-export-320.png", fullPage: true });
});
