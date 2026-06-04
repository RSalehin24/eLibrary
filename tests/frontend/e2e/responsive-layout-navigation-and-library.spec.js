import { expect, test } from "./support/playwright";
import { createSessionPayload, createBook, mockAuthenticatedSession, mockCatalogBooksApi, mockAccessApi, mockProfileApi, mockManualBooksApi, mockPropertyPagesApi, mockProcessingApi, assertNoPageOverflow, getGridColumnCount, expectFirstBookCoverToFillCardWidth, getMobileNavPanelMetrics, expectAccessUsersShellScrollable, expectAccessUsersHeaderLayout, expectMobileProcessingCardShellToPeekNextCard, expectProcessingInlineFilterCountLayout, expectTableCardMode, expectMobileTableCellToFillCard, expectDesktopTableMode, expectElementsNotOverlapping } from "./responsive-layout/index.js";
test.describe("responsive layout navigation and library coverage", () => {
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: { cookies: [], origins: [] } });

  test("desktop baseline keeps routed large-screen layouts in desktop mode", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 1440,
      height: 900
    });
    await mockAuthenticatedSession(page, {
      capabilities: ["processing:manage"],
      is_superuser: true
    });
    await mockCatalogBooksApi(page, 24, {
      savedFilters: [{
        id: 1,
        name: "Recently reviewed books"
      }]
    });
    await mockAccessApi(page, 24);
    await mockProcessingApi(page);
    await mockProfileApi(page);
    await page.goto("/home");
    await expect(page.getByRole("heading", {
      name: "All Books",
      exact: true
    })).toBeVisible();
    await expect(page.getByRole("navigation", {
      name: "Primary"
    })).toBeVisible();
    await expect(page.getByTestId("mobile-nav-trigger")).toBeHidden();
    expect(await getGridColumnCount(page, ".book-grid")).toBe(2);
    await assertNoPageOverflow(page);
    await page.goto("/library");
    await expect(page.getByRole("heading", {
      name: "Books",
      exact: true
    })).toBeVisible();
    await expectDesktopTableMode(page, ".book-table");
    await assertNoPageOverflow(page);
    await page.goto("/access");
    await expect(page.getByRole("heading", {
      name: "Users & Access",
      exact: true
    })).toBeVisible();
    await expectDesktopTableMode(page, ".access-users-table");
    await expectAccessUsersHeaderLayout(page);
    await expectAccessUsersShellScrollable(page);
    expect(await getGridColumnCount(page, ".access-user-editor-primary-row")).toBeGreaterThan(1);
    await assertNoPageOverflow(page);
    await page.goto("/catalog");
    await expect(page.getByRole("heading", {
      name: "Catalog",
      exact: true
    })).toBeVisible();
    await expectDesktopTableMode(page, ".processing-table");
    await assertNoPageOverflow(page);
    await page.goto("/profile");
    await page.getByRole("button", {
      name: "Edit"
    }).click();
    expect(await getGridColumnCount(page, ".profile-form-grid")).toBe(2);
    await assertNoPageOverflow(page);
  });
  test("tablet landscape keeps desktop nav without topbar overlap", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 1024,
      height: 768
    });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page);
    await page.goto("/home");
    await expect(page.getByRole("navigation", {
      name: "Primary"
    })).toBeVisible();
    await expect(page.getByTestId("mobile-nav-trigger")).toBeHidden();
    await expectElementsNotOverlapping(page, [".brand-block", ".topnav", ".session-box"]);
    await assertNoPageOverflow(page);
  });
  test("route changes start at the top after scrolling the previous page", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 1440,
      height: 900
    });
    await mockAuthenticatedSession(page, {
      capabilities: ["processing:manage"],
      is_superuser: true
    });
    await mockCatalogBooksApi(page, 96);
    await mockAccessApi(page, 12);
    await page.goto("/home");
    await expect(page.getByRole("heading", {
      name: "All Books",
      exact: true
    })).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect.poll(async () => page.evaluate(() => window.scrollY)).toBeGreaterThan(300);
    await page.getByRole("link", {
      name: "Users & Access",
      exact: true
    }).click();
    await expect(page.getByRole("heading", {
      name: "Users & Access",
      exact: true
    })).toBeVisible();
    await expect.poll(async () => page.evaluate(() => window.scrollY)).toBe(0);
  });
  test("small tablet header uses the mobile drawer", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 820,
      height: 1180
    });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page);
    await page.goto("/home");
    await expect(page.getByRole("navigation", {
      name: "Primary"
    })).toBeHidden();
    await expect(page.getByTestId("mobile-nav-trigger")).toBeVisible();
    await page.getByTestId("mobile-nav-trigger").click();
    await expect(page.locator("#app-mobile-nav")).toBeVisible();
    await expect(page.getByRole("link", {
      name: "My Books"
    })).toBeVisible();
    await assertNoPageOverflow(page);
  });
  test("tablet portrait uses the mobile drawer while keeping a two-column book grid", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 768,
      height: 1024
    });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page);
    await page.goto("/home");
    await expect(page.getByTestId("mobile-nav-trigger")).toBeVisible();
    await page.getByTestId("mobile-nav-trigger").click();
    await expect(page.locator("#app-mobile-nav")).toBeVisible();
    await expect(page.getByRole("link", {
      name: "My Books"
    })).toBeVisible();
    await page.getByRole("button", {
      name: "Book Properties"
    }).click();
    await expect(page.getByRole("link", {
      name: "Books",
      exact: true
    })).toBeVisible();
    expect(await getGridColumnCount(page, ".book-grid")).toBe(2);
    await assertNoPageOverflow(page);
  });
  test("phone home view uses the mobile drawer and a single-column card grid", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 390,
      height: 844
    });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page);
    await page.goto("/home");
    await expect(page.getByTestId("mobile-nav-trigger")).toBeVisible();
    await page.getByTestId("mobile-nav-trigger").click();
    await expect(page.locator("#app-mobile-nav")).toBeVisible();
    await expect(page.getByRole("button", {
      name: "Processing"
    })).toBeVisible();
    expect(await getGridColumnCount(page, ".book-grid")).toBe(1);
    await expectFirstBookCoverToFillCardWidth(page);
    await page.goto("/created-books");
    await expect(page.getByRole("heading", {
      name: "My Books",
      exact: true
    })).toBeVisible();
    expect(await getGridColumnCount(page, ".book-grid")).toBe(1);
    await expectFirstBookCoverToFillCardWidth(page);
    await assertNoPageOverflow(page);
  });
  test("phone mobile drawer collapses to content when processing links are unavailable", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 390,
      height: 844
    });
    await mockAuthenticatedSession(page, {
      is_staff: false,
      is_superuser: false,
      capabilities: []
    });
    await mockCatalogBooksApi(page);
    await page.goto("/home");
    await page.getByTestId("mobile-nav-trigger").click();
    await expect(page.locator("#app-mobile-nav")).toBeVisible();
    await expect(page.getByRole("button", {
      name: "Processing"
    })).toHaveCount(0);
    const panelMetrics = await getMobileNavPanelMetrics(page);
    expect(panelMetrics.height).toBeLessThan(panelMetrics.viewportHeight - 120);
    expect(panelMetrics.bottomGap).toBeGreaterThanOrEqual(40);
    await assertNoPageOverflow(page);
  });
  test("phone library organizes the toolbar and cardifies the table", async ({
    page
  }) => {
    await page.setViewportSize({
      width: 390,
      height: 844
    });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page, 24, {
      savedFilters: [{
        id: 1,
        name: "Architecture books"
      }, {
        id: 2,
        name: "Needs review and manual follow-up"
      }]
    });
    await page.goto("/library");
    await expect(page.getByRole("heading", {
      name: "Books",
      exact: true
    })).toBeVisible();
    await expect(page.getByRole("button", {
      name: "CSV export"
    })).toBeVisible();
    await expect(page.locator(".saved-filter-apply").filter({
      hasText: "Needs review and manual follow-up"
    })).toBeVisible();
    const toolbarLayout = await page.locator(".catalog-page-header--property-layout").evaluate(header => {
      const headerBox = header.getBoundingClientRect();
      const searchBox = header.querySelector(".catalog-search-field").getBoundingClientRect();
      const filterButton = header.querySelector(".catalog-filter-toggle");
      const filterBox = filterButton.getBoundingClientRect();
      const sortBox = header.querySelector(".catalog-search-sort").getBoundingClientRect();
      const countBox = header.querySelector(".catalog-result-count").getBoundingClientRect();
      const extraBox = header.querySelector(".catalog-search-actions-extra").getBoundingClientRect();
      const exportButtons = [...header.querySelectorAll(".export-action-button")].map(button => button.getBoundingClientRect());
      return {
        countRightGap: Math.round(headerBox.right - countBox.right),
        countTopGap: Math.round(countBox.top - headerBox.top),
        exportButtonTopGap: exportButtons.length === 2 ? Math.abs(Math.round(exportButtons[0].top - exportButtons[1].top)) : null,
        exportButtonsCombinedWidth: exportButtons.length === 2 ? Math.round(exportButtons[0].width + exportButtons[1].width + (exportButtons[1].left - exportButtons[0].right)) : 0,
        extraWidth: Math.round(extraBox.width),
        filterGap: getComputedStyle(filterButton).columnGap,
        filterWidth: Math.round(filterBox.width),
        filterSortCombinedWidth: Math.round(
          Math.max(filterBox.right, sortBox.right) -
            Math.min(filterBox.left, sortBox.left)
        ),
        filterSortTopGap: Math.abs(Math.round(filterBox.top - sortBox.top)),
        headerWidth: Math.round(headerBox.width),
        searchLeftGap: Math.round(searchBox.left - headerBox.left),
        searchRightGap: Math.round(headerBox.right - searchBox.right),
        sortWidth: Math.round(sortBox.width)
      };
    });
    expect(toolbarLayout.countRightGap).toBeLessThanOrEqual(1);
    expect(toolbarLayout.countTopGap).toBeLessThanOrEqual(1);
    expect(toolbarLayout.exportButtonTopGap).toBeLessThanOrEqual(1);
    expect(toolbarLayout.exportButtonsCombinedWidth).toBe(toolbarLayout.extraWidth);
    expect(toolbarLayout.filterGap).toBe("6px");
    expect(toolbarLayout.filterSortCombinedWidth).toBe(toolbarLayout.headerWidth);
    expect(toolbarLayout.filterSortTopGap).toBeLessThanOrEqual(1);
    expect(toolbarLayout.filterWidth).toBeLessThan(toolbarLayout.sortWidth);
    expect(toolbarLayout.searchLeftGap).toBeLessThanOrEqual(1);
    expect(toolbarLayout.searchRightGap).toBeLessThanOrEqual(1);
    await expectTableCardMode(page, ".book-table");
    await assertNoPageOverflow(page);
  });
});
