import { expect, test } from "./support/playwright";
import { loginAsSuperAdmin } from "./support/liveApp";

function isCatalogBooksResponse(response, expectedPage = null, expectedLimit = null) {
  if (!response.url().includes("/api/catalog/books/?")) {
    return false;
  }

  const url = new URL(response.url());
  if (expectedPage !== null && url.searchParams.get("page") !== String(expectedPage)) {
    return false;
  }
  if (expectedLimit !== null && url.searchParams.get("limit") !== String(expectedLimit)) {
    return false;
  }

  return response.status() === 200;
}

test.describe("library live app", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page);
  });

  test("library page uses 60-row incremental fetches against the live app", async ({
    page,
  }) => {
    const firstResponsePromise = page.waitForResponse((response) =>
      isCatalogBooksResponse(response, 1, 60),
    );

    await page.goto("/library");
    await expect(
      page.getByRole("heading", { name: "Books", exact: true }),
    ).toBeVisible({ timeout: 15_000 });

    const firstResponse = await firstResponsePromise;
    expect(new URL(firstResponse.url()).searchParams.get("page")).toBe("1");
    expect(new URL(firstResponse.url()).searchParams.get("limit")).toBe("60");

    const sortedResponsePromise = page.waitForResponse((response) =>
      isCatalogBooksResponse(response, 1, 60) &&
      new URL(response.url()).searchParams.get("sort") === "title",
    );
    await page
      .locator(".catalog-search-sort .catalog-toolbar-select")
      .selectOption("title");
    await sortedResponsePromise;

    await expect(page.locator(".book-table tbody tr").first()).toBeVisible();
  });
});
