import { expect, test } from "./support/playwright";
import { loginAsSuperAdmin } from "./support/liveApp";
import { seedData } from "./support/seedData";

test.describe("Auth Pages", () => {
  test("sign in reaches the live catalog and search narrows the visible books", async ({
    page,
  }) => {
    await loginAsSuperAdmin(page);

    await expect(
      page.getByRole("heading", { name: seedData.books.homePrimary.title }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: seedData.books.homeSecondary.title }),
    ).toBeVisible();

    const search = page.getByPlaceholder(
      "Search all books by title, book ID, or writer...",
    );
    await search.fill("Companion");
    await search.press("Enter");

    await expect(
      page.getByRole("heading", { name: seedData.books.homeSecondary.title }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: seedData.books.homePrimary.title }),
    ).toHaveCount(0);
  });

  test("home page renders the shared inline card controls", async ({ page }) => {
    await loginAsSuperAdmin(page);

    await expect(page.locator(".book-card").first()).toBeVisible();
    await expect(
      page.locator(".catalog-search-sort .catalog-toolbar-select"),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Filters" })).toBeVisible();
  });
});
