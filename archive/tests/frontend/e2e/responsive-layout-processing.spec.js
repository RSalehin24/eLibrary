import { expect, test } from "./support/playwright";
import { assertNoPageOverflow, expectMobileProcessingCardShellToPeekNextCard, expectProcessingInlineFilterCountLayout, expectTableCardMode, getGridColumnCount, mockAuthenticatedSession, mockCatalogBooksApi, mockProcessingApi } from "./responsive-layout/index.js";

test.describe("responsive layout processing coverage", () => {
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: { cookies: [], origins: [] } });

  test("phone processing catalog page reflows summary cards and renders dense rows as mobile cards", async ({
    page,
  }) => {
    async function getAutomationHeaderLayout(testId) {
      return page.getByTestId(testId).evaluate((card) => {
        const header = card.querySelector(".processing-card-head--settings");
        const title = header
          .querySelector(".processing-card-head-meta h2")
          .getBoundingClientRect();
        const controls = header
          .querySelector(".processing-card-head-controls")
          .getBoundingClientRect();

        return {
          sameRow:
            controls.top < title.bottom && controls.bottom > title.top,
        };
      });
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await mockAuthenticatedSession(page);
    await mockCatalogBooksApi(page, 0);
    await mockProcessingApi(page);

    await page.goto("/catalog");

    await expect(
      page.getByRole("heading", { name: "Catalog", exact: true }),
    ).toBeVisible();
    await expect(page.getByTestId("catalog-records-table")).toBeVisible();
    expect(await getGridColumnCount(page, ".processing-card-grid")).toBe(1);
    const processingCardLayout = await page
      .getByTestId("catalog-records-card")
      .evaluate((card) => {
        const titleRow = card
          .querySelector(".processing-card-title-row")
          .getBoundingClientRect();
        const countBox = card
          .querySelector('[data-testid="catalog-records-count"]')
          .getBoundingClientRect();
        const filterButton = card.querySelector(".catalog-filter-toggle");
        const filterBox = filterButton.getBoundingClientRect();
        const actionsBox = card
          .querySelector(".processing-card-head-actions")
          .getBoundingClientRect();
        const actionButtonBox = card
          .querySelector('[data-testid="catalog-records-create-btn"]')
          .getBoundingClientRect();

        return {
          actionFillsActions: Math.round(
            actionsBox.width - actionButtonBox.width,
          ),
          actionRightGap: Math.round(actionsBox.right - actionButtonBox.right),
          actionStartsBelowFilter: actionButtonBox.top >= filterBox.bottom - 1,
          countRightGap: Math.round(titleRow.right - countBox.right),
          countCenterDelta: Math.round(
            Math.abs(
              countBox.top +
                countBox.height / 2 -
                (titleRow.top + titleRow.height / 2),
            ),
          ),
          filterGap: getComputedStyle(filterButton).columnGap,
          filterWidth: Math.round(filterBox.width),
          actionWidth: Math.round(actionButtonBox.width),
        };
      });
    expect(processingCardLayout.countRightGap).toBeLessThanOrEqual(1);
    expect(processingCardLayout.countCenterDelta).toBeLessThanOrEqual(1);
    expect(processingCardLayout.filterGap).toBe("6px");
    expect(processingCardLayout.filterWidth).toBeLessThan(
      processingCardLayout.actionWidth,
    );
    expect(processingCardLayout.actionStartsBelowFilter).toBe(true);
    expect(processingCardLayout.actionFillsActions).toBeLessThanOrEqual(1);
    expect(processingCardLayout.actionRightGap).toBeLessThanOrEqual(1);
    const automationHeaderLayout = await getAutomationHeaderLayout(
      "catalog-automation-card",
    );
    expect(automationHeaderLayout.sameRow).toBe(true);
    await expectTableCardMode(page, ".processing-table", {
      cellDisplay: ["grid", "inline-flex"],
    });
    const processingCellLayout = await page
      .getByTestId("catalog-records-table")
      .evaluate((table) => {
        const row = table.querySelector("tbody tr");
        const nameCell = table.querySelector("tbody td.processing-col-name");
        const selectCell = table.querySelector("tbody td.processing-col-select");
        const nameCellStyle = getComputedStyle(nameCell);
        const selectCellStyle = getComputedStyle(selectCell);
        const rowBox = row.getBoundingClientRect();
        const nameCellBox = nameCell.getBoundingClientRect();

        return {
          cellDisplay: nameCellStyle.display,
          gridTemplateColumns: nameCellStyle.gridTemplateColumns,
          rowCellWidthDelta: Math.round(rowBox.width - nameCellBox.width),
          selectCellDisplay: selectCellStyle.display,
        };
      });
    expect(processingCellLayout.cellDisplay).toBe("grid");
    expect(processingCellLayout.gridTemplateColumns).not.toBe("none");
    expect(processingCellLayout.rowCellWidthDelta).toBeLessThanOrEqual(2);
    expect(processingCellLayout.selectCellDisplay).toBe("inline-flex");
    await expectMobileProcessingCardShellToPeekNextCard(
      page,
      "catalog-records-card",
    );
    await assertNoPageOverflow(page);

    await page.goto("/processing-incomplete-check");
    await expect(
      page.getByRole("heading", {
        name: "Incomplete",
        exact: true,
        level: 1,
      }),
    ).toBeVisible();
    await expectProcessingInlineFilterCountLayout(
      page,
      "incomplete-records-card",
    );
    await expectProcessingInlineFilterCountLayout(
      page,
      "incomplete-completed-card",
    );
    const incompleteAutomationHeaderLayout = await getAutomationHeaderLayout(
      "incomplete-automation-card",
    );
    expect(incompleteAutomationHeaderLayout.sameRow).toBe(true);
    await assertNoPageOverflow(page);
  });
});
