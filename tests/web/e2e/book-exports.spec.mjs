import { readFile } from "node:fs/promises";
import { test, expect, fixture, useAccount } from "./fixtures.mjs";

test("catalog exports include the applied search and print the entire filtered list in another tab", async ({ page, context }) => {
  await page.goto(`/catalog/?q=${encodeURIComponent(fixture.query)}`);
  const controls = page.getByRole("region", { name: "বইয়ের তালিকা ডাউনলোড", exact: true });
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

test("physical inventory supports filters, grouped XLSX and a direct manual-book creation action on a phone", async ({ page }) => {
  await useAccount(page, "administrator");
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto(`/physical-books/?q=${encodeURIComponent(fixture.personal.paper.title)}&binding=hard_cover`);
  await expect(page.getByRole("heading", { name: fixture.personal.paper.title, exact: true })).toBeVisible();
  const controls = page.getByRole("region", { name: "বইয়ের তালিকা ডাউনলোড", exact: true });
  await controls.getByLabel("ভাগ করুন", { exact: true }).selectOption("publisher");
  const downloadEvent = page.waitForEvent("download");
  await controls.getByRole("button", { name: "XLSX", exact: true }).click();
  const download = await downloadEvent;
  const workbook = await readFile(await download.path());
  expect(workbook.subarray(0, 2).toString()).toBe("PK");
  expect(download.suggestedFilename()).toBe("physical-books.xlsx");
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-artifacts/foundation/physical-inventory-320.png", fullPage: true });
  await page.getByRole("link", { name: "কাগজের বই যোগ করুন", exact: true }).click();
  await expect(page.getByLabel("বইয়ের ধরন", { exact: true })).toHaveValue("manual");
});
