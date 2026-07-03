import { expect, test } from "./support/playwright";
import { assertNoPageOverflow, getGridColumnCount, mockAuthenticatedSession, mockManualBooksApi, mockProfileApi } from "./responsive-layout/index.js";

test.describe("responsive layout manual books and profile coverage", () => {
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: { cookies: [], origins: [] } });

  test("phone manual books page stacks toolbar actions and composer fields", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await mockAuthenticatedSession(page);
    await mockManualBooksApi(page);

    await page.goto("/manual-books");

    await expect(
      page.getByRole("heading", { name: "Physical Books' List", exact: true }),
    ).toBeVisible();

    const manualToolbarLayout = await page
      .locator(".catalog-page-header--property-layout")
      .evaluate((header) => {
        const extraBox = header
          .querySelector(".catalog-search-actions-extra")
          .getBoundingClientRect();
        const addButtonBox = header
          .querySelector('[aria-label="Add manual book"]')
          .getBoundingClientRect();
        return {
          addButtonRightGap: Math.round(extraBox.right - addButtonBox.right),
          addButtonWidth: Math.round(addButtonBox.width),
          extraWidth: Math.round(extraBox.width),
        };
      });
    expect(manualToolbarLayout.addButtonRightGap).toBeLessThanOrEqual(1);
    expect(manualToolbarLayout.addButtonWidth).toBeLessThanOrEqual(48);

    // Expand the collapsible download row
    await page.getByRole("button", { name: "Export options" }).click();
    await expect(page.locator(".manual-books-download-row")).toBeVisible();

    // Verify all 3 export buttons (CSV, PDF, Excel) are within the download
    // row and do not overflow the mobile viewport horizontally
    const downloadRowLayout = await page
      .locator(".manual-books-download-row")
      .evaluate((row) => {
        const rowBox = row.getBoundingClientRect();
        const exportButtons = [...row.querySelectorAll(".export-action-button")];
        const buttonBoxes = exportButtons.map((b) => b.getBoundingClientRect());
        const allButtonsInRow = buttonBoxes.every(
          (b) => b.left >= rowBox.left - 2 && b.right <= rowBox.right + 2,
        );
        const noHorizontalOverflow = buttonBoxes.every(
          (b) => b.right <= window.innerWidth + 2,
        );
        return {
          buttonCount: exportButtons.length,
          allButtonsInRow,
          noHorizontalOverflow,
        };
      });
    expect(downloadRowLayout.buttonCount).toBe(3);
    expect(downloadRowLayout.allButtonsInRow).toBe(true);
    expect(downloadRowLayout.noHorizontalOverflow).toBe(true);

    await page.getByRole("button", { name: "Add manual book" }).click();
    await expect(page.locator("#manual-book-composer")).toBeVisible();
    // Wait for the form to be fully rendered and layout to settle
    await expect(page.locator("#manual-book-composer textarea")).toBeVisible();
    const manualFormColumns = await page
      .locator(".manual-book-form-grid")
      .evaluateAll((nodes) =>
        nodes.map((node) => {
          const columns = getComputedStyle(node).gridTemplateColumns.trim();
          if (!columns || columns === "none") {
            return 0;
          }
          return columns.split(/\s+/).length;
        }),
      );
    expect(manualFormColumns.length).toBeGreaterThan(0);
    expect(manualFormColumns.every((columnCount) => columnCount === 1)).toBe(
      true,
    );
    await assertNoPageOverflow(page);
  });



  test("narrow phone profile editor keeps stacked sections readable at 320px", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await mockAuthenticatedSession(page, {
      is_superuser: false,
      is_staff: false,
      capabilities: [],
    });
    await mockProfileApi(page);

    await page.goto("/profile");

    await expect(
      page.getByRole("heading", { name: "Profile", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Edit" }).click();
    await expect(
      page.getByRole("heading", { name: "Change Password" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Expand" }).first().click();
    expect(await getGridColumnCount(page, ".profile-form-grid")).toBe(1);
    expect(await getGridColumnCount(page, ".profile-password-grid")).toBe(1);
    await page.getByRole("button", { name: "Save Changes" }).scrollIntoViewIfNeeded();
    await expect(page.getByRole("button", { name: "Save Changes" })).toBeVisible();
    await assertNoPageOverflow(page);
  });
});
