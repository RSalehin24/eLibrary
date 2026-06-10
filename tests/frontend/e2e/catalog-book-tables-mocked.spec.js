import { expect, test } from "./support/playwright";

const sessionPayload = {
  authenticated: true,
  user: {
    id: 1,
    email: "catalog-admin@example.com",
    full_name: "Catalog Admin",
    is_active: true,
    is_staff: true,
    is_superuser: true,
    capabilities: [],
    totp_enabled: false,
    totp_required: false,
    totp_setup_required: false,
  },
};

const pageVariants = [
  { path: "/library", heading: "Books", view: "table" },
  { path: "/home", heading: "All Books", view: "cards" },
  { path: "/created-books", heading: "My Books", view: "cards" },
];

function createDeferred() {
  let release;
  const promise = new Promise((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

function createBook(index, overrides = {}) {
  const bookNumber = String(index + 1).padStart(3, "0");
  return {
    id: `book-${bookNumber}`,
    slug: `catalog-book-${bookNumber}`,
    catalog_code: `BK-${bookNumber}`,
    title: `Catalog Book ${bookNumber}`,
    authors: [`Writer ${bookNumber}`],
    categories: [`Category ${index % 4}`],
    series: index % 2 === 0 ? [`Series ${index % 3}`] : [],
    record_type: index % 5 === 0 ? "manual" : "digital",
    created_at: `2026-04-${String((index % 28) + 1).padStart(2, "0")}T08:00:00Z`,
    primary_source: {
      display_path: `source/${bookNumber}`,
    },
    is_in_my_books: false,
    my_books_added_at: null,
    ...overrides,
  };
}

async function mockAuthenticatedSession(page) {
  await page.route("**/api/auth/session/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload),
    });
  });
  await page.route("**/api/csrf/", async (route) => {
    await route.fulfill({ status: 204, body: "" });
  });
}

async function mockCatalogBooksApi(page, total = 75, options = {}) {
  const ownedBookIndexes = new Set(options.ownedBookIndexes || []);
  const books = Array.from({ length: total }, (_, index) =>
    createBook(index, {
      is_in_my_books: ownedBookIndexes.has(index),
      my_books_added_at: ownedBookIndexes.has(index)
        ? "2026-04-20T08:00:00Z"
        : null,
    }),
  );
  const pageTwoRequest = createDeferred();
  const requestLog = [];

  await page.route("**/api/catalog/books/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/my-books/")) {
      if (options.myBooksActionDelay) {
        await options.myBooksActionDelay.promise;
      }
      const slug = decodeURIComponent(
        url.pathname.split("/").filter(Boolean).at(-2) || "",
      );
      const book = books.find((candidate) => candidate.slug === slug);
      if (!book) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Not found." }),
        });
        return;
      }
      if (route.request().method() === "DELETE") {
        book.is_in_my_books = false;
        book.my_books_added_at = null;
        await route.fulfill({ status: 204, body: "" });
        return;
      }
      book.is_in_my_books = true;
      book.my_books_added_at = "2026-04-21T08:00:00Z";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(book),
      });
      return;
    }

    const currentPage = Number(url.searchParams.get("page") || "1");
    const limit = Number(url.searchParams.get("limit") || "60");
    const query = String(url.searchParams.get("q") || "").trim().toLowerCase();
    const scopedBooks =
      url.searchParams.get("ownership") === "mine"
        ? books.filter((book) => book.is_in_my_books)
        : books;
    const filteredBooks = query
      ? scopedBooks.filter((book) => book.title.toLowerCase().includes(query))
      : scopedBooks;

    requestLog.push({
      page: currentPage,
      limit,
      sort: url.searchParams.get("sort") || "",
    });

    if (currentPage === 2) {
      await pageTwoRequest.promise;
    }

    const startIndex = (currentPage - 1) * limit;
    const entries = filteredBooks.slice(startIndex, startIndex + limit);

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entries,
        pagination: {
          page: currentPage,
          limit,
          total_count: filteredBooks.length,
          page_count: Math.max(1, Math.ceil(filteredBooks.length / limit)),
          has_previous: currentPage > 1,
          has_next: startIndex + entries.length < filteredBooks.length,
        },
      }),
    });
  });

  await page.route("**/api/saved-filters/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  return {
    releasePageTwo: pageTwoRequest.release,
    requestLog,
  };
}

test("Books table My Books action shows an immediate centered loader", async ({
  page,
}) => {
  await mockAuthenticatedSession(page);
  const actionDelay = createDeferred();
  await mockCatalogBooksApi(page, 3, { myBooksActionDelay: actionDelay });

  await page.goto("/library");
  const addButton = page.getByRole("button", {
    name: "Add Catalog Book 001 to My Books",
  });
  await expect(addButton).toBeVisible();

  await addButton.click();
  await expect(addButton).toBeDisabled();
  await expect(addButton).toHaveAttribute("aria-busy", "true");
  await expect(addButton).toHaveText("Adding...");
  await expect(addButton.locator(".button-label-spinner-slot")).toHaveCount(2);
  const labelColumns = await addButton
    .locator(".button-label--stable")
    .evaluate((node) => getComputedStyle(node).gridTemplateColumns.split(" "));
  expect(labelColumns[0]).toBe(labelColumns[2]);

  actionDelay.release();
  const removeButton = page.getByRole("button", {
    name: "Remove Catalog Book 001 from My Books",
  });
  await expect(removeButton).toBeEnabled();
  const removeCentering = await removeButton.evaluate((button) => {
    const buttonBox = button.getBoundingClientRect();
    const labelBox = button
      .querySelector(".button-label-text")
      .getBoundingClientRect();
    return {
      buttonCenter: buttonBox.left + buttonBox.width / 2,
      labelCenter: labelBox.left + labelBox.width / 2,
    };
  });
  expect(Math.abs(removeCentering.buttonCenter - removeCentering.labelCenter)).toBeLessThan(1);
});

test("My Books cards expose a compact non-red remove action", async ({
  page,
}) => {
  await mockAuthenticatedSession(page);
  await mockCatalogBooksApi(page, 3, { ownedBookIndexes: [0] });

  await page.goto("/created-books");
  await expect(page.getByRole("heading", { name: "My Books" })).toBeVisible();
  const removeButton = page.locator(".book-card-remove-button").first();
  await expect(removeButton).toBeVisible();

  const buttonStyles = await removeButton.evaluate((node) => {
    const styles = getComputedStyle(node);
    return {
      position: styles.position,
      top: styles.top,
      right: styles.right,
      backgroundColor: styles.backgroundColor,
      width: styles.width,
      height: styles.height,
    };
  });
  expect(buttonStyles.position).toBe("absolute");
  expect(buttonStyles.top).not.toBe("auto");
  expect(buttonStyles.right).not.toBe("auto");
  expect(buttonStyles.backgroundColor).not.toBe("rgb(220, 38, 38)");
  expect(Number.parseFloat(buttonStyles.width)).toBeGreaterThanOrEqual(38);
  expect(Number.parseFloat(buttonStyles.height)).toBeGreaterThanOrEqual(38);
});

for (const pageVariant of pageVariants) {
  test(`${pageVariant.heading} uses shared inline controls and incremental loading`, async ({
    page,
  }) => {
    await mockAuthenticatedSession(page);
    const { releasePageTwo, requestLog } = await mockCatalogBooksApi(
      page,
      75,
      {
        ownedBookIndexes:
          pageVariant.path === "/created-books"
            ? Array.from({ length: 75 }, (_, index) => index)
            : [],
      },
    );

    await page.goto(pageVariant.path);
    await expect(
      page.getByRole("heading", { name: pageVariant.heading, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".catalog-result-count")).toHaveText("75");

    const actionClasses = await page
      .locator(".catalog-search-actions > *")
      .evaluateAll((nodes) => nodes.map((node) => node.className));
    expect(actionClasses[0]).toContain("catalog-search-sort");
    expect(actionClasses[1]).toContain("catalog-filter-toggle");
    expect(actionClasses[2]).toContain("catalog-result-count");
    expect(requestLog[0].page).toBe(1);
    expect(requestLog[0].limit).toBe(60);

    if (pageVariant.view === "table") {
      await expect(page.locator(".book-table tbody tr")).toHaveCount(60);
      await page.locator(".book-table tbody tr").nth(30).scrollIntoViewIfNeeded();
      await expect(page.getByTestId("book-table-load-more-skeleton")).toBeVisible();
    } else {
      await expect(
        page.locator(".book-card:not(.book-card-skeleton)"),
      ).toHaveCount(60);
      await page
        .locator(".book-card:not(.book-card-skeleton)")
        .nth(30)
        .scrollIntoViewIfNeeded();
      await expect(page.getByTestId("book-grid-load-more-skeleton")).toBeVisible();
    }

    releasePageTwo();

    if (pageVariant.view === "table") {
      await expect(page.locator(".book-table tbody tr")).toHaveCount(75);
    } else {
      await expect(
        page.locator(".book-card:not(.book-card-skeleton)"),
      ).toHaveCount(75);
    }
    expect(requestLog.some((entry) => entry.page === 2 && entry.limit === 60)).toBe(
      true,
    );
  });
}
