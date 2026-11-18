import { expect, test } from "./support/playwright";
import { ManualBooksPageModel } from "./pages/manualBooksPage";
import { loginAsSuperAdmin } from "./support/liveApp";

test.describe("Manual Books Page", () => {
  test("creating a manual book through the live form keeps it searchable in the browser", async ({
    page,
  }, testInfo) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    const uniqueTitle = `E2E Manual Book ${testInfo.parallelIndex + 1} ${Date.now()}`;

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    await manualBooksPage.fillTitle(uniqueTitle);
    await manualBooksPage.addTag("Writer", "E2E Writer");
    await manualBooksPage.addTag("Category", "E2E Fiction");
    await manualBooksPage.submit();

    await manualBooksPage.search(uniqueTitle);
    await expect(page.getByText(uniqueTitle, { exact: true })).toBeVisible();
  });

  test("creating a manual book by committing tags on blur without pressing enter", async ({
    page,
  }, testInfo) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    const uniqueTitle = `Blur Commit Book ${testInfo.parallelIndex + 1} ${Date.now()}`;

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    await manualBooksPage.fillTitle(uniqueTitle);
    
    // Fill values but DO NOT press Enter
    await manualBooksPage.fillTagWithoutEnter("Writer", "Blur Writer");
    await manualBooksPage.fillTagWithoutEnter("Category", "Blur Fiction");
    
    // Submit directly - the blur should trigger tag commit automatically
    await manualBooksPage.submit();

    // Verify book is created successfully and visible in search
    await manualBooksPage.search(uniqueTitle);
    await expect(page.getByText(uniqueTitle, { exact: true })).toBeVisible();
  });

  test("clicking Done with a filled form saves the book, closes the composer, and refreshes the page", async ({
    page,
  }, testInfo) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    const uniqueTitle = `Done Save Book ${testInfo.parallelIndex + 1} ${Date.now()}`;

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    await manualBooksPage.fillTitle(uniqueTitle);
    
    await manualBooksPage.fillTagWithoutEnter("Writer", "Done Writer");
    await manualBooksPage.fillTagWithoutEnter("Category", "Done Fiction");
    
    // Click Done
    await manualBooksPage.clickDone();

    // The composer should be closed
    await manualBooksPage.expectComposerVisible(false);

    // Verify book is created successfully and visible
    await manualBooksPage.search(uniqueTitle);
    await expect(page.getByText(uniqueTitle, { exact: true })).toBeVisible();
  });

  test("clicking Done with an empty form closes the composer without saving", async ({
    page,
  }) => {
    const manualBooksPage = new ManualBooksPageModel(page);

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    
    // Click Done immediately
    await manualBooksPage.clickDone();

    // The composer should be closed
    await manualBooksPage.expectComposerVisible(false);
  });

  test("clicking Done with invalid/incomplete input keeps composer open showing error", async ({
    page,
  }, testInfo) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    const uniqueTitle = `Invalid Book ${testInfo.parallelIndex + 1} ${Date.now()}`;

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    
    // Fill title but leave required Writer and Category fields empty
    await manualBooksPage.fillTitle(uniqueTitle);
    
    await manualBooksPage.clickDone();

    // The composer should STILL be visible due to the validation failure
    await manualBooksPage.expectComposerVisible(true);
  });

  test("closing the composer via the toolbar close button saves the book if there is input", async ({
    page,
  }, testInfo) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    const uniqueTitle = `Toolbar Save Book ${testInfo.parallelIndex + 1} ${Date.now()}`;

    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();
    await manualBooksPage.openComposer();
    await manualBooksPage.fillTitle(uniqueTitle);
    
    await manualBooksPage.fillTagWithoutEnter("Writer", "Toolbar Writer");
    await manualBooksPage.fillTagWithoutEnter("Category", "Toolbar Fiction");
    
    // Click the toolbar button to close/toggle the composer
    await manualBooksPage.closeComposerWithToolbar();

    // The composer should be closed
    await manualBooksPage.expectComposerVisible(false);

    // Verify book is created successfully and visible
    await manualBooksPage.search(uniqueTitle);
    await expect(page.getByText(uniqueTitle, { exact: true })).toBeVisible();
  });

  test("sort dropdown has code sort removed and publisher sort added", async ({
    page,
  }) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();

    const sortSelect = page.locator(".catalog-search-sort .catalog-toolbar-select");
    await expect(sortSelect).toBeVisible();

    const options = await sortSelect.locator("option").evaluateAll((opts) =>
      opts.map((o) => ({ value: o.value, text: o.text }))
    );

    const values = options.map((o) => o.value);
    
    // Code sort options must be removed
    expect(values).not.toContain("catalog_code");
    expect(values).not.toContain("-catalog_code");

    // Publisher sort options must be present
    expect(values).toContain("manual_publisher");
    expect(values).toContain("-manual_publisher");

    const labels = options.map((o) => o.text);
    expect(labels).toContain("Publisher A-Z");
    expect(labels).toContain("Publisher Z-A");
  });

  test("filters drawer contains the correct new fields", async ({
    page,
  }) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();

    // Open filter drawer
    const filterToggle = page.getByRole("button", { name: /Filter/i });
    await expect(filterToggle).toBeVisible();
    await filterToggle.click();

    // Verify all expected filter fields exist in the drawer grid
    const expectedFilters = [
      "Writer",
      "Translator",
      "Editor",
      "Category",
      "Publisher",
      "Binding"
    ];

    for (const label of expectedFilters) {
      const fieldLocator = page.locator(".catalog-filter-field", {
        has: page.getByText(label, { exact: true })
      });
      await expect(fieldLocator).toBeVisible();
    }

    // Verify Binding select options
    const bindingSelect = page.locator(".catalog-filter-field", {
      has: page.getByText("Binding", { exact: true })
    }).locator("select");
    
    await expect(bindingSelect).toBeVisible();
    const bindingOptions = await bindingSelect.locator("option").evaluateAll((opts) =>
      opts.map((o) => o.text)
    );
    expect(bindingOptions).toContain("Any");
    expect(bindingOptions).toContain("Hardcover");
    expect(bindingOptions).toContain("Paperback");
  });

  test("Excel export with group-by select options is functional", async ({
    page,
  }) => {
    const manualBooksPage = new ManualBooksPageModel(page);
    await loginAsSuperAdmin(page);
    await manualBooksPage.goto();

    // Toggle export tools row open
    await page.getByRole("button", { name: "Export options" }).click();

    // Verify group-by select is present
    const groupBySelect = page.locator(".manual-books-download-row select");
    await expect(groupBySelect).toBeVisible();

    const options = await groupBySelect.locator("option").evaluateAll((opts) =>
      opts.map((o) => o.text)
    );
    expect(options).toContain("No grouping");
    expect(options).toContain("Category");
    expect(options).toContain("Publisher");
    expect(options).toContain("Binding");
    expect(options).toContain("Language");
    expect(options).toContain("Contributor");

    // Select Grouping and trigger download check
    await groupBySelect.selectOption("category");
    
    const excelBtn = page.getByRole("button", { name: "Excel export", exact: true });
    await expect(excelBtn).toBeVisible();

    // Listen for download event
    const downloadPromise = page.waitForEvent("download");
    await excelBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("manual-books.xlsx");
  });
});

