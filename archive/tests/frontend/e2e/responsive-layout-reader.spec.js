import { expect, test } from "./support/playwright";
import { loginAsSuperAdmin } from "./support/liveApp";
import { seedData } from "./support/seedData";
import { assertNoPageOverflow } from "./responsive-layout/index.js";

test.describe("responsive live reader coverage", () => {
  test("book detail and reader stay contained at landscape tablet size", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 844, height: 390 });
    await loginAsSuperAdmin(page);

    await page.goto(`/books/${seedData.books.detail.slug}`);
    await expect(page.getByTestId("book-detail-hero")).toBeVisible();
    await assertNoPageOverflow(page);

    await page.getByTestId("book-open-reader-button").click();
    await expect(page).toHaveURL(/\/reader\?/);
    await expect(page.locator("#reader-view")).toBeVisible();
    await expect(page.locator("#viewer iframe")).toBeVisible({
      timeout: 15_000,
    });
    await assertNoPageOverflow(page);
  });

  test("phone reader settings menu remains fully visible", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await loginAsSuperAdmin(page);

    await page.goto(`/books/${seedData.books.detail.slug}`);
    await page.getByTestId("book-open-reader-button").click();
    await expect(page).toHaveURL(/\/reader\?/);
    await expect(page.locator("#reader-view")).toBeVisible();
    await expect(page.locator("#viewer iframe")).toBeVisible({
      timeout: 15_000,
    });

    const tocToggle = page.getByRole("button", {
      name: "Toggle table of contents",
    });
    await expect(tocToggle).toHaveAttribute("aria-expanded", "true");
    await tocToggle.click();
    await expect(tocToggle).toHaveAttribute("aria-expanded", "false");
    await expect
      .poll(() =>
        page
          .locator(".reader-wrapper")
          .evaluate((wrapper) => wrapper.getBoundingClientRect().width),
      )
      .toBeGreaterThan(300);

    const settingsButton = page.getByRole("button", {
      name: "Open reading settings",
    });
    const settingsPanel = page.locator("#reader-settings-panel");

    await settingsButton.click();
    await expect(settingsPanel).toHaveAttribute("aria-hidden", "false");
    await expect(settingsPanel).toBeVisible();

    const bounds = await settingsPanel.evaluate((panel) => {
      const panelRect = panel.getBoundingClientRect();
      const readerRect = document
        .querySelector(".reader-wrapper")
        ?.getBoundingClientRect();

      return {
        panelLeft: panelRect.left,
        panelRight: panelRect.right,
        readerLeft: readerRect?.left ?? 0,
        readerRight: readerRect?.right ?? window.innerWidth,
        viewportRight: window.innerWidth,
      };
    });

    expect(bounds.panelLeft).toBeGreaterThanOrEqual(bounds.readerLeft - 1);
    expect(bounds.panelRight).toBeLessThanOrEqual(
      Math.min(bounds.readerRight, bounds.viewportRight) + 1,
    );
  });
});
