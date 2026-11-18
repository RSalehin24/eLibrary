import { expect, test } from "./support/playwright";
import { CatalogPropertyPageModel } from "./pages/catalogPropertyPage";
import { loginAsSuperAdmin } from "./support/liveApp";
import { seedData } from "./support/seedData";

test.describe("Catalog Navigation Pages", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page);
  });

  test("categories search can open the filtered library results", async ({
    page,
  }) => {
    const categoriesPage = new CatalogPropertyPageModel(page, {
      path: "/categories",
      heading: "Categories",
      searchPlaceholder: "Search categories or codes...",
    });

    await categoriesPage.goto();
    await categoriesPage.search(seedData.catalogFilters.category);
    await categoriesPage.openResult(seedData.catalogFilters.category);

    await expect(page).toHaveURL(/\/library/);
    await expect(
      page.getByRole("link", { name: seedData.books.homePrimary.title }),
    ).toBeVisible();
  });

  test("series search can open the matching library shelf", async ({ page }) => {
    const seriesPage = new CatalogPropertyPageModel(page, {
      path: "/series",
      heading: "Series",
      searchPlaceholder: "Search series or codes...",
    });

    await seriesPage.goto();
    await seriesPage.search(seedData.catalogFilters.series);
    await seriesPage.openResult(seedData.catalogFilters.series);

    await expect(page).toHaveURL(/\/library/);
    await expect(
      page.getByRole("link", { name: seedData.books.homeSecondary.title }),
    ).toBeVisible();
  });

  test("writers search can open the author-filtered library view", async ({
    page,
  }) => {
    const writersPage = new CatalogPropertyPageModel(page, {
      path: "/writers",
      heading: "Writers",
      searchPlaceholder: "Search writers or codes...",
    });

    await writersPage.goto();
    await writersPage.search(seedData.catalogFilters.writer);
    await writersPage.openResult(seedData.catalogFilters.writer);

    await expect(page).toHaveURL(/\/library/);
    await expect(
      page.getByRole("link", { name: seedData.books.access.title }),
    ).toBeVisible();
  });

  test("created books search keeps seeded owned books visible", async ({
    page,
  }) => {
    await page.goto("/created-books");
    await expect(
      page.getByRole("heading", { name: "My Books", exact: true }),
    ).toBeVisible();

    const search = page.getByPlaceholder("Search your books by title or book ID...");
    await search.fill(seedData.books.detail.title);
    await search.press("Enter");

    await expect(
      page.getByRole("heading", { name: /E2E Detail Book/ }),
    ).toBeVisible();
  });
});
