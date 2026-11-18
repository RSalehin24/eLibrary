import { expect } from "../support/playwright";
export async function assertNoPageOverflow(page) {
  const overflow = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.width + 2);
}
export async function getGridColumnCount(page, selector) {
  return page.locator(selector).evaluate(node => {
    const columns = getComputedStyle(node).gridTemplateColumns.trim();
    if (!columns || columns === "none") {
      return 0;
    }
    return columns.split(/\s+/).length;
  });
}
export async function expectFirstBookCoverToFillCardWidth(page) {
  const metrics = await page.locator(".book-card").first().evaluate(card => {
    const art = card.querySelector(".book-card-art");
    const cover = card.querySelector(".book-card-cover");
    const cardStyle = getComputedStyle(card);
    const cardBox = card.getBoundingClientRect();
    const artBox = art.getBoundingClientRect();
    const coverBox = cover.getBoundingClientRect();
    const paddingLeft = Number.parseFloat(cardStyle.paddingLeft) || 0;
    const paddingRight = Number.parseFloat(cardStyle.paddingRight) || 0;
    return {
      artWidthGap: Math.round(cardBox.width - paddingLeft - paddingRight - artBox.width),
      coverWidthGap: Math.round(artBox.width - coverBox.width)
    };
  });
  expect(metrics.artWidthGap).toBeLessThanOrEqual(2);
  expect(metrics.coverWidthGap).toBeLessThanOrEqual(1);
}
export async function getMobileNavPanelMetrics(page) {
  return page.locator("#app-mobile-nav").evaluate(panel => {
    const panelBox = panel.getBoundingClientRect();
    return {
      bottomGap: Math.round(window.innerHeight - panelBox.bottom),
      height: Math.round(panelBox.height),
      viewportHeight: window.innerHeight
    };
  });
}
export async function expectAccessUsersShellScrollable(page) {
  const metrics = await page.locator(".access-users-table-shell").evaluate(shell => ({
    overflowY: getComputedStyle(shell).overflowY,
    scrollable: shell.scrollHeight > shell.clientHeight
  }));
  expect(["auto", "scroll"]).toContain(metrics.overflowY);
  expect(metrics.scrollable).toBe(true);
}
export async function expectAccessUsersHeaderLayout(page, {
  mobile = false
} = {}) {
  const metrics = await page.getByTestId("access-users-section").evaluate(section => {
    const toolbar = section.querySelector(".access-users-toolbar");
    const title = toolbar.querySelector("h2").getBoundingClientRect();
    const search = toolbar.querySelector(".access-users-search-field").getBoundingClientRect();
    const count = toolbar.querySelector(".access-users-result-count").getBoundingClientRect();
    const filter = toolbar.querySelector(".access-users-filter-field").getBoundingClientRect();
    const sort = toolbar.querySelector(".access-users-sort-field").getBoundingClientRect();
    const filterSelect = toolbar.querySelector(".access-users-filter-field select");
    const sortSelect = toolbar.querySelector(".access-users-sort-field select");
    return {
      countRightGap: Math.round(toolbar.getBoundingClientRect().right - count.right),
      searchAfterTitleGap: Math.round(search.left - title.right),
      searchBeforeCountGap: Math.round(count.left - search.right),
      toolbarLabelCount: toolbar.querySelectorAll(".catalog-toolbar-inline-label").length,
      filterFirstOptionDisabled: filterSelect?.options?.[0]?.disabled === true && filterSelect?.options?.[0]?.text === "Filter",
      sortFirstOptionDisabled: sortSelect?.options?.[0]?.disabled === true && sortSelect?.options?.[0]?.text === "Sort",
      sameTopLine: search.top < title.bottom && count.top < title.bottom && title.top < search.bottom,
      filterSharesTitleRow: filter.top < title.bottom && title.top < filter.bottom,
      filterBelowTitle: filter.top >= title.bottom - 1,
      sortSharesFilterRow: Math.abs(sort.top - filter.top) <= 1 || sort.top < filter.bottom && filter.top < sort.bottom
    };
  });
  expect(metrics.sameTopLine).toBe(true);
  expect(metrics.countRightGap).toBeLessThanOrEqual(1);
  expect(metrics.toolbarLabelCount).toBe(0);
  expect(metrics.filterFirstOptionDisabled).toBe(true);
  expect(metrics.sortFirstOptionDisabled).toBe(true);
  if (mobile) {
    expect(metrics.searchAfterTitleGap).toBeGreaterThanOrEqual(6);
    expect(metrics.searchBeforeCountGap).toBeGreaterThanOrEqual(6);
    expect(metrics.filterBelowTitle).toBe(true);
    expect(metrics.sortSharesFilterRow).toBe(true);
  } else {
    expect(metrics.searchAfterTitleGap).toBeGreaterThanOrEqual(8);
    expect(metrics.searchBeforeCountGap).toBeGreaterThanOrEqual(8);
    expect(metrics.filterSharesTitleRow).toBe(true);
    expect(metrics.sortSharesFilterRow).toBe(true);
  }
}
export async function expectMobileProcessingCardShellToPeekNextCard(page, cardTestId) {
  const metrics = await page.getByTestId(cardTestId).evaluate(card => {
    const shell = card.querySelector(".processing-table-shell");
    const rows = [...card.querySelectorAll(".processing-table tbody tr")];
    const firstRow = rows[0];
    const secondRow = rows[1];
    const shellBox = shell.getBoundingClientRect();
    const firstRowBox = firstRow.getBoundingClientRect();
    const secondRowBox = secondRow.getBoundingClientRect();
    const shellStyle = getComputedStyle(shell);
    return {
      overflowY: shellStyle.overflowY,
      scrollable: shell.scrollHeight > shell.clientHeight,
      firstRowFullyVisible: firstRowBox.top >= shellBox.top - 1 && firstRowBox.bottom <= shellBox.bottom + 1,
      secondRowStartsVisible: secondRowBox.top < shellBox.bottom - 8,
      secondRowClipped: secondRowBox.bottom > shellBox.bottom + 8
    };
  });
  expect(["auto", "scroll"]).toContain(metrics.overflowY);
  expect(metrics.scrollable).toBe(true);
  expect(metrics.firstRowFullyVisible).toBe(true);
  expect(metrics.secondRowStartsVisible).toBe(true);
  expect(metrics.secondRowClipped).toBe(true);
}
export async function expectProcessingInlineFilterCountLayout(page, cardTestId) {
  const metrics = await page.getByTestId(cardTestId).evaluate(card => {
    const title = card.querySelector(".processing-card-head-meta h2").getBoundingClientRect();
    const tools = card.querySelector(".processing-card-head-inline-tools");
    const filter = tools.querySelector(".catalog-filter-toggle").getBoundingClientRect();
    const count = tools.querySelector(".processing-card-title-count").getBoundingClientRect();
    return {
      titleLeftOfFilter: title.left < filter.left,
      titleSharesRowWithFilter: title.top < filter.bottom && filter.top < title.bottom,
      filterLeftOfCount: filter.left < count.left,
      sameRow: filter.top < count.bottom && count.top < filter.bottom
    };
  });
  expect(metrics.sameRow).toBe(true);
  expect(metrics.titleLeftOfFilter).toBe(true);
  expect(metrics.titleSharesRowWithFilter).toBe(true);
  expect(metrics.filterLeftOfCount).toBe(true);
}
export async function expectTableCardMode(page, selector, {
  cellDisplay = "grid"
} = {}) {
  const state = await page.locator(selector).evaluate(table => {
    const thead = table.querySelector("thead");
    const firstRow = table.querySelector("tbody tr");
    const firstCell = table.querySelector("tbody td[data-label]");
    return {
      theadDisplay: thead ? getComputedStyle(thead).display : "",
      rowDisplay: firstRow ? getComputedStyle(firstRow).display : "",
      cellDisplay: firstCell ? getComputedStyle(firstCell).display : "",
      firstLabel: firstCell?.getAttribute("data-label") || ""
    };
  });
  expect(state.theadDisplay).toBe("none");
  expect(state.rowDisplay).toBe("block");
  if (Array.isArray(cellDisplay)) {
    expect(cellDisplay).toContain(state.cellDisplay);
  } else {
    expect(state.cellDisplay).toBe(cellDisplay);
  }
  expect(state.firstLabel).not.toBe("");
}
export async function expectMobileTableCellToFillCard(page, selector, cellSelector) {
  const state = await page.locator(selector).evaluate((table, nextCellSelector) => {
    const row = table.querySelector("tbody tr");
    const cell = table.querySelector(nextCellSelector);
    return {
      cellWidth: cell ? Math.round(cell.getBoundingClientRect().width) : 0,
      rowWidth: row ? Math.round(row.getBoundingClientRect().width) : 0
    };
  }, cellSelector);
  expect(state.rowWidth - state.cellWidth).toBeLessThanOrEqual(2);
}
export async function expectDesktopTableMode(page, selector) {
  const state = await page.locator(selector).evaluate(table => {
    const thead = table.querySelector("thead");
    const firstRow = table.querySelector("tbody tr");
    const firstCell = table.querySelector("tbody td");
    return {
      theadDisplay: thead ? getComputedStyle(thead).display : "",
      rowDisplay: firstRow ? getComputedStyle(firstRow).display : "",
      cellDisplay: firstCell ? getComputedStyle(firstCell).display : ""
    };
  });
  expect(state.theadDisplay).not.toBe("none");
  expect(state.rowDisplay).toBe("table-row");
  expect(state.cellDisplay).toBe("table-cell");
}
export async function expectElementsNotOverlapping(page, selectors) {
  const overlaps = await page.evaluate(nextSelectors => {
    const rects = nextSelectors.map(selector => {
      const element = document.querySelector(selector);
      if (!element) {
        return {
          selector,
          missing: true
        };
      }
      const rect = element.getBoundingClientRect();
      return {
        selector,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
        visible: rect.width > 0 && rect.height > 0
      };
    });
    const collisions = [];
    for (let index = 0; index < rects.length; index += 1) {
      const left = rects[index];
      if (left.missing || !left.visible) {
        continue;
      }
      for (let otherIndex = index + 1; otherIndex < rects.length; otherIndex += 1) {
        const right = rects[otherIndex];
        if (right.missing || !right.visible) {
          continue;
        }
        const intersects = !(left.right <= right.left || right.right <= left.left || left.bottom <= right.top || right.bottom <= left.top);
        if (intersects) {
          collisions.push([left.selector, right.selector]);
        }
      }
    }
    return collisions;
  }, selectors);
  expect(overlaps).toEqual([]);
}
