import { expect, test } from "./support/playwright";
import { loginAsSuperAdmin } from "./support/liveApp";
import { seedData } from "./support/seedData";

test.describe("Home Page Filter Pages", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page);
  });

  test("selecting an author filters series and categories dynamically", async ({ page }) => {
    // 1. Navigate to home page
    await page.goto("/home");

    // 2. Expand filters
    const filterToggle = page.getByRole("button", { name: /Filter/i });
    await filterToggle.click();

    // 3. Find the Author dropdown trigger
    // Since it's a SearchableSelect, the trigger shows the current label (default "Any")
    // Let's locate the triggers by label
    const authorTrigger = page.locator(".catalog-filter-field", {
      has: page.getByText("Author", { exact: true })
    }).locator(".custom-select-trigger");

    await expect(authorTrigger).toBeVisible();
    await authorTrigger.click();

    // Search and select E2E Writer
    const authorSearchInput = page.locator(".catalog-filter-field", {
      has: page.getByText("Author", { exact: true })
    }).locator(".custom-select-search-input");
    
    await authorSearchInput.fill(seedData.catalogFilters.writer);
    
    const authorOption = page.locator(".catalog-filter-field", {
      has: page.getByText("Author", { exact: true })
    }).getByRole("button", { name: seedData.catalogFilters.writer, exact: true });
    
    await authorOption.click();

    // Wait for the async options update to complete
    await page.waitForTimeout(2000);

    // 4. Check if Series options are restricted
    const seriesTrigger = page.locator(".catalog-filter-field", {
      has: page.getByText("Series", { exact: true })
    }).locator(".custom-select-trigger");
    await seriesTrigger.click();

    // Get the option list buttons for Series
    const seriesOptions = page.locator(".catalog-filter-field", {
      has: page.getByText("Series", { exact: true })
    }).locator(".custom-select-option-button");

    // E2E Writer has books only in E2E Starter Series
    const seriesLabels = await seriesOptions.allInnerTexts();
    console.log("Seeded series options under E2E Writer:", seriesLabels);
    
    // It should contain "Any" and "E2E Starter Series" but not other unrelated series
    expect(seriesLabels).toContain("E2E Starter Series");
    
    // Close the series dropdown
    await seriesTrigger.click();

    // 5. Check if Category options are restricted
    const categoryTrigger = page.locator(".catalog-filter-field", {
      has: page.getByText("Category", { exact: true })
    }).locator(".custom-select-trigger");
    await categoryTrigger.click();

    const categoryOptions = page.locator(".catalog-filter-field", {
      has: page.getByText("Category", { exact: true })
    }).locator(".custom-select-option-button");

    const categoryLabels = await categoryOptions.allInnerTexts();
    console.log("Seeded category options under E2E Writer:", categoryLabels);

    expect(categoryLabels).toContain("E2E Fiction");
  });
});
