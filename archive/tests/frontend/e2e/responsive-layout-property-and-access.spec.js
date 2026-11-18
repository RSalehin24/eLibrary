import { expect, test } from "./support/playwright";
import { assertNoPageOverflow, expectAccessUsersHeaderLayout, expectAccessUsersShellScrollable, expectMobileTableCellToFillCard, expectTableCardMode, getGridColumnCount, mockAccessApi, mockAuthenticatedSession, mockPropertyPagesApi } from "./responsive-layout/index.js";

function createDeferred() {
  let release;
  const promise = new Promise((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

async function mockDeferredContributorTabs(page) {
  const tabData = {
    writers: "Writer Stable",
    translators: "Translator Stable",
    editors: "Editor Stable",
    publishers: "Publisher Stable",
  };
  const gates = Object.fromEntries(
    Object.keys(tabData).map((key) => [key, createDeferred()]),
  );

  for (const [endpoint, name] of Object.entries(tabData)) {
    await page.route(`**/api/catalog/${endpoint}/**`, async (route) => {
      await gates[endpoint].promise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          entries: [
            {
              id: `${endpoint}-1`,
              catalog_code: "WRT-001",
              name,
              book_count: 3,
              digital_book_count: 2,
              manual_book_count: 1,
              created_at: "2026-04-20T08:00:00Z",
            },
          ],
          pagination: {
            page: 1,
            limit: 60,
            total_count: 1,
            page_count: 1,
            has_previous: false,
            has_next: false,
          },
        }),
      });
    });
  }

  return gates;
}

test.describe("responsive layout property and access coverage", () => {
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: { cookies: [], origins: [] } });

  test("phone book property pages render mobile table items like the books page", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await mockAuthenticatedSession(page);
    await mockPropertyPagesApi(page);

    await page.goto("/categories");
    await expect(
      page.getByRole("heading", { name: "Categories", exact: true }),
    ).toBeVisible();
    await expectTableCardMode(page, ".property-table");
    await expectMobileTableCellToFillCard(
      page,
      ".property-table",
      'tbody td[data-label="Name"]',
    );
    await assertNoPageOverflow(page);

    await page.goto("/series");
    await expect(
      page.getByRole("heading", { name: "Series", exact: true }),
    ).toBeVisible();
    await expectTableCardMode(page, ".property-table");
    await expectMobileTableCellToFillCard(
      page,
      ".property-table",
      'tbody td[data-label="Series"]',
    );
    await assertNoPageOverflow(page);

    await page.goto("/writers");
    await expect(
      page.getByRole("heading", { name: "Writers", exact: true }),
    ).toBeVisible();
    await expectTableCardMode(page, ".property-table");
    await expectMobileTableCellToFillCard(
      page,
      ".property-table",
      'tbody td[data-label="Name"]',
    );
    await assertNoPageOverflow(page);
  });

  test("writer tabs keep table structure stable while each tab loads", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page);
    const gates = await mockDeferredContributorTabs(page);

    await page.goto("/writers");
    await expect(page.getByTestId("property-table-table-skeleton")).toBeVisible();
    await expect(page.locator(".property-table col")).toHaveCount(7);
    await expect(page.locator(".property-table thead th")).toHaveCount(7);
    gates.writers.release();
    await expect(page.getByText("Writer Stable")).toBeVisible();

    await page.getByRole("link", { name: "Translators" }).click();
    await expect(page.getByText("Writer Stable")).toHaveCount(0);
    await expect(page.getByTestId("property-table-table-skeleton")).toBeVisible();
    await expect(page.locator(".property-table col")).toHaveCount(7);
    gates.translators.release();
    await expect(page.getByText("Translator Stable")).toBeVisible();

    await page.getByRole("link", { name: "Editors" }).click();
    await expect(page.getByText("Translator Stable")).toHaveCount(0);
    await expect(page.getByTestId("property-table-table-skeleton")).toBeVisible();
    await expect(page.locator(".property-table col")).toHaveCount(7);
    gates.editors.release();
    await expect(page.getByText("Editor Stable")).toBeVisible();

    await page.getByRole("link", { name: "Publishers" }).click();
    await expect(page.getByText("Editor Stable")).toHaveCount(0);
    await expect(page.getByTestId("property-table-table-skeleton")).toBeVisible();
    await expect(page.locator(".property-table col")).toHaveCount(7);
    gates.publishers.release();
    await expect(page.getByText("Publisher Stable")).toBeVisible();
  });

  test("phone access page stacks form fields and cardifies the users table", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await mockAuthenticatedSession(page);
    await mockAccessApi(page, 24);

    await page.goto("/access");

    await expect(
      page.getByRole("heading", { name: "Users & Access", exact: true }),
    ).toBeVisible();
    await expect(page.getByTestId("access-user-form")).toBeVisible();
    expect(await getGridColumnCount(page, ".access-user-editor-primary-row")).toBe(1);
    await expectAccessUsersHeaderLayout(page, { mobile: true });
    await expectAccessUsersShellScrollable(page);
    await expectTableCardMode(page, ".access-users-table");
    await assertNoPageOverflow(page);
  });
});
