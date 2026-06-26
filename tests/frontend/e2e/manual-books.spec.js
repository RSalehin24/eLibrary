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
});
