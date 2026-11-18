import { expect, test } from "./support/playwright";

function createDeferred() {
  let release;
  const promise = new Promise((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

function authenticatedSessionPayload() {
  return {
    authenticated: true,
    user: {
      id: 1,
      email: "superadmin@example.com",
      full_name: "Super Admin",
      profile_image_url: "",
      is_active: true,
      is_staff: true,
      is_superuser: true,
      totp_enabled: false,
      totp_required: false,
      totp_setup_required: false,
      capabilities: [],
    },
  };
}

function unauthenticatedSessionPayload() {
  return {
    authenticated: false,
    user: null,
  };
}

test.describe("Page Loader Skeletons", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test(
    "catalog property pages keep the header visible and show an in-table skeleton while loading",
    async ({ page }) => {
      const categoriesRequest = createDeferred();

      await page.route("**/api/auth/session/", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(authenticatedSessionPayload()),
        });
      });
      await page.route("**/api/csrf/", async (route) => {
        await route.fulfill({ status: 204, body: "" });
      });
      await page.route("**/api/catalog/categories/**", async (route) => {
        await categoriesRequest.promise;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      });

      await page.goto("/categories");
      await expect(
        page.getByRole("heading", { name: "Categories" }),
      ).toBeVisible();
      await expect(
        page.getByTestId("property-table-table-skeleton"),
      ).toBeVisible();

      categoriesRequest.release();
      await expect(
        page.getByTestId("property-table-table-skeleton"),
      ).toHaveCount(0);
    },
  );

  test(
    "contributor tabs replace stale rows with a skeleton while the next tab loads",
    async ({ page }) => {
      const translatorsRequest = createDeferred();

      await page.route("**/api/auth/session/", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(authenticatedSessionPayload()),
        });
      });
      await page.route("**/api/csrf/", async (route) => {
        await route.fulfill({ status: 204, body: "" });
      });
      await page.route("**/api/catalog/writers/**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "writer-1",
              catalog_code: "WRT-001",
              name: "Writer One",
              book_count: 8,
              digital_book_count: 6,
              manual_book_count: 2,
              created_at: "2026-04-21T08:00:00Z",
            },
          ]),
        });
      });
      await page.route("**/api/catalog/translators/**", async (route) => {
        await translatorsRequest.promise;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "translator-1",
              catalog_code: "TRN-001",
              name: "Translator One",
              book_count: 5,
              digital_book_count: 4,
              manual_book_count: 1,
              created_at: "2026-04-21T09:00:00Z",
            },
          ]),
        });
      });

      await page.goto("/writers");
      await expect(
        page.getByRole("heading", { name: "Writers" }),
      ).toBeVisible();
      await expect(page.getByText("Writer One")).toBeVisible();

      await page.getByRole("link", { name: "Translators", exact: true }).click();
      await expect(
        page.getByRole("heading", { name: "Translators" }),
      ).toBeVisible();
      await expect(
        page.getByTestId("property-table-table-skeleton"),
      ).toBeVisible();
      await expect(page.getByText("Writer One")).toHaveCount(0);

      translatorsRequest.release();
      await expect(
        page.getByTestId("property-table-table-skeleton"),
      ).toHaveCount(0);
      await expect(page.getByText("Translator One")).toBeVisible();
    },
  );

  test("admin pages show a management skeleton while admin data is loading", async ({
    page,
  }) => {
    const adminDataRequest = createDeferred();

    await page.route("**/api/auth/session/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(authenticatedSessionPayload()),
      });
    });
    await page.route("**/api/csrf/", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });
    await page.route("**/api/auth/users/**", async (route) => {
      await adminDataRequest.promise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          rows: [],
          pagination: {
            offset: 0,
            limit: 60,
            totalCount: 0,
            hasMore: false,
            nextOffset: 0,
          },
        }),
      });
    });
    await page.route("**/api/access/grants/", async (route) => {
      await adminDataRequest.promise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/api/access/references/**", async (route) => {
      await adminDataRequest.promise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          users: [],
          books: [],
          categories: [],
          writers: [],
          account_scopes: [],
          scoped_scopes: [],
        }),
      });
    });

    await page.goto("/access");
    await expect(page.locator(".page-loader-variant-management")).toBeVisible();

    adminDataRequest.release();
    await expect(
      page.getByRole("heading", { name: "Users & Access" }),
    ).toBeVisible();
    await expect(page.locator(".page-loader-variant-management")).toHaveCount(0);
  });

  test("auth pages show an auth skeleton while session state is loading", async ({
    page,
  }) => {
    const sessionRequest = createDeferred();

    await page.route("**/api/auth/session/", async (route) => {
      await sessionRequest.promise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(unauthenticatedSessionPayload()),
      });
    });
    await page.route("**/api/csrf/", async (route) => {
      await route.fulfill({ status: 204, body: "" });
    });
    await page.route("**/api/auth/password-reset/validate/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Password link is valid.",
        }),
      });
    });

    await page.goto("/create-password?uid=loader-uid&token=loader-token");
    await expect(page.locator(".page-loader-variant-auth")).toBeVisible();

    sessionRequest.release();
    await expect(
      page.getByRole("heading", { name: "Create password" }),
    ).toBeVisible();
    await expect(page.locator(".page-loader-variant-auth")).toHaveCount(0);
  });
});
