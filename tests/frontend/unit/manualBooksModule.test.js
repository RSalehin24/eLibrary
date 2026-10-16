import assert from "node:assert/strict";
import test from "node:test";
import {
  MANUAL_BOOKS_EXPORT_STORAGE_KEY,
  emptyManualBookForm,
  defaultManualBookFilters,
  manualBookFilterFields,
  manualBookToolbarFields,
  manualBookSortOptions,
} from "../../../app/frontend/src/features/manual-books/manualBookFilters.js";
import { toQueryString, normalizeCatalogListPayload, loadManualBookOptions, mergeContributorSuggestions, createManualBook, loadManualBooksForExport } from '../support/manual-books-fixtures.js';


// ---------------------------------------------------------------------------
// 1. manualBookFilters.js Tests
// ---------------------------------------------------------------------------

test("emptyManualBookForm defaults binding to hard_cover", () => {
  assert.equal(emptyManualBookForm.binding, "hard_cover");
  assert.equal(emptyManualBookForm.title, "");
  assert.deepEqual(emptyManualBookForm.writers, []);
  assert.deepEqual(emptyManualBookForm.categories, []);
  assert.equal(emptyManualBookForm.publisher, "");
  assert.equal(emptyManualBookForm.price, "");
});


test("defaultManualBookFilters default states are correct", () => {
  assert.deepEqual(defaultManualBookFilters, {
    q: "",
    writer: "",
    translator: "",
    editor: "",
    category: "",
    publisher: "",
    binding: "",
    ownership: "",
    record_type: "manual",
    sort: "-created_at",
  });
});


test("MANUAL_BOOKS_EXPORT_STORAGE_KEY is correct", () => {
  assert.equal(MANUAL_BOOKS_EXPORT_STORAGE_KEY, "manual-books-export");
});


test("manualBookToolbarFields excludes sort field", () => {
  const hasSort = manualBookToolbarFields.some((field) => field.key === "sort");
  assert.ok(!hasSort, "Toolbar fields must not contain sort");
  assert.ok(manualBookToolbarFields.length > 0);
});


test("manualBookSortOptions matches sort options mapping", () => {
  assert.ok(manualBookSortOptions.length > 0);
  const newestFirst = manualBookSortOptions.find((o) => o.value === "-created_at");
  assert.ok(newestFirst);
  assert.equal(newestFirst.label, "Newest first");
});


// ---------------------------------------------------------------------------
// 2. manualBookOptions.js Tests
// ---------------------------------------------------------------------------

test("mergeContributorSuggestions de-duplicates case-insensitively and sorts A-Z", () => {
  const payload = [
    [{ name: "Humayun Ahmed" }, { name: "humayun ahmed" }],
    [{ name: "Zafar Iqbal" }],
    [{ name: "  Humayun Ahmed  " }, { name: "Anisul Hoque" }],
  ];
  const merged = mergeContributorSuggestions(payload);
  assert.deepEqual(merged, [
    "Anisul Hoque",
    "Humayun Ahmed",
    "Zafar Iqbal",
  ]);
});


test("loadManualBookOptions fetches and structures all option values (including publishers)", async () => {
  const fetchedUrls = [];
  const catalogFetchMock = async (url) => {
    fetchedUrls.push(url);
    if (url.includes("/categories/")) return [{ name: "Science Fiction" }, { name: "Drama" }];
    if (url.includes("/writers/")) return [{ name: "Humayun Ahmed" }];
    if (url.includes("/translators/")) return [{ name: "Bob Translator" }];
    if (url.includes("/editors/")) return [{ name: "Carol Editor" }];
    if (url.includes("/series/")) return [{ name: "Himur Boi" }];
    if (url.includes("/publishers/")) return [{ name: "Prothoma" }, { name: "Anyaprokash" }];
    return [];
  };

  const options = await loadManualBookOptions(catalogFetchMock);

  // Assert correct URLs fetched
  assert.deepEqual(fetchedUrls.sort(), [
    "/catalog/categories/?record_type=all&sort=name",
    "/catalog/editors/?record_type=all&sort=name",
    "/catalog/publishers/?record_type=all&sort=name",
    "/catalog/series/?record_type=all&sort=name",
    "/catalog/translators/?record_type=all&sort=name",
    "/catalog/writers/?record_type=all&sort=name"
  ].sort());

  // Assert options parsed correctly
  assert.deepEqual(options.categories, ["Science Fiction", "Drama"]);
  assert.deepEqual(options.series, ["Himur Boi"]);
  assert.deepEqual(options.publishers, ["Prothoma", "Anyaprokash"]);
  assert.deepEqual(options.contributors, [
    "Bob Translator",
    "Carol Editor",
    "Humayun Ahmed",
  ]);
});


// ---------------------------------------------------------------------------
// 3. manualBookCreate.js Tests
// ---------------------------------------------------------------------------

test("createManualBook formats empty string price to null", async () => {
  let sentBody = null;
  const catalogFetchMock = async (url, opts) => {
    sentBody = opts.body;
    return { id: 1 };
  };

  const form = {
    title: "Test Book",
    price: "",
    binding: "hard_cover",
  };

  await createManualBook(form, catalogFetchMock);
  assert.equal(sentBody.price, null, "Empty price string should be converted to null");
});


test("createManualBook preserves non-empty price values", async () => {
  let sentBody = null;
  const catalogFetchMock = async (url, opts) => {
    sentBody = opts.body;
    return { id: 1 };
  };

  const form = {
    title: "Test Book",
    price: "499.50",
    binding: "hard_cover",
  };

  await createManualBook(form, catalogFetchMock);
  assert.equal(sentBody.price, "499.50");
});


// ---------------------------------------------------------------------------
// 4. manualBookExport.js Tests
// ---------------------------------------------------------------------------

test("loadManualBooksForExport paginates over all pages and aggregates entries", async () => {
  const fetchedUrls = [];
  const catalogFetchMock = async (url) => {
    fetchedUrls.push(url);
    if (url.includes("page=1")) {
      return {
        entries: [{ id: 101, title: "Book One" }],
        pagination: {
          page: 1,
          limit: 100,
          total_count: 3,
          page_count: 3,
          has_previous: false,
          has_next: true,
        },
      };
    }
    if (url.includes("page=2")) {
      return {
        entries: [{ id: 102, title: "Book Two" }],
        pagination: {
          page: 2,
          limit: 100,
          total_count: 3,
          page_count: 3,
          has_previous: true,
          has_next: true,
        },
      };
    }
    if (url.includes("page=3")) {
      return {
        entries: [{ id: 103, title: "Book Three" }],
        pagination: {
          page: 3,
          limit: 100,
          total_count: 3,
          page_count: 3,
          has_previous: true,
          has_next: false,
        },
      };
    }
    throw new Error(`Unexpected paginated URL: ${url}`);
  };

  const filters = { q: "", record_type: "manual" };
  const allBooks = await loadManualBooksForExport(filters, catalogFetchMock);

  assert.deepEqual(fetchedUrls, [
    "/catalog/manual-books/?record_type=manual&page=1&limit=100",
    "/catalog/manual-books/?record_type=manual&page=2&limit=100",
    "/catalog/manual-books/?record_type=manual&page=3&limit=100",
  ]);

  assert.equal(allBooks.length, 3);
  assert.deepEqual(allBooks, [
    { id: 101, title: "Book One" },
    { id: 102, title: "Book Two" },
    { id: 103, title: "Book Three" },
  ]);
});
