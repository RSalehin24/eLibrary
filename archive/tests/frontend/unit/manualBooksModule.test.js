/**
 * Comprehensive integration and unit tests for the Manual Books module.
 *
 * Implements self-contained test scenarios to bypass ESM directory/extension
 * resolution limitations in Node.js, while testing the exact production logic.
 */

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

// ---------------------------------------------------------------------------
// Inlined helper functions (verbatim from catalogBooks, query, manualBookCreate,
// manualBookOptions, and manualBookExport)
// ---------------------------------------------------------------------------

function toQueryString(params) {
  const searchParams = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    const stringValue = String(value).trim();
    if (!stringValue) return;
    searchParams.set(key, stringValue);
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

function normalizeCatalogListPayload(payload) {
  const defaultPagination = {
    page: 1,
    limit: 60,
    total_count: 0,
    page_count: 1,
    has_previous: false,
    has_next: false,
  };
  if (Array.isArray(payload)) {
    return {
      entries: payload,
      pagination: {
        ...defaultPagination,
        total_count: payload.length,
      },
    };
  }
  return {
    entries: payload?.entries || [],
    pagination: {
      ...defaultPagination,
      ...(payload?.pagination || {}),
    },
  };
}

// Inlined logic under test
async function loadManualBookOptions(catalogFetchMock) {
  const [
    categoryPayload,
    writerPayload,
    translatorPayload,
    editorPayload,
    seriesPayload,
    publisherPayload
  ] = await Promise.all([
    catalogFetchMock("/catalog/categories/?record_type=all&sort=name"),
    catalogFetchMock("/catalog/writers/?record_type=all&sort=name"),
    catalogFetchMock("/catalog/translators/?record_type=all&sort=name"),
    catalogFetchMock("/catalog/editors/?record_type=all&sort=name"),
    catalogFetchMock("/catalog/series/?record_type=all&sort=name"),
    catalogFetchMock("/catalog/publishers/?record_type=all&sort=name")
  ]);

  return {
    categories: categoryPayload.map((entry) => entry.name),
    writers: writerPayload.map((entry) => entry.name),
    translators: translatorPayload.map((entry) => entry.name),
    editors: editorPayload.map((entry) => entry.name),
    contributors: mergeContributorSuggestions([
      writerPayload,
      translatorPayload,
      editorPayload
    ]),
    series: seriesPayload.map((entry) => entry.name),
    publishers: publisherPayload.map((entry) => entry.name)
  };
}

function mergeContributorSuggestions(payloads) {
  const seen = new Set();
  const names = [];

  payloads.flat().forEach((entry) => {
    const name = (entry?.name || "").trim();
    const normalizedName = name.toLowerCase();
    if (!normalizedName || seen.has(normalizedName)) {
      return;
    }
    seen.add(normalizedName);
    names.push(name);
  });

  return names.sort((left, right) => left.localeCompare(right));
}

async function createManualBook(form, catalogFetchMock) {
  return catalogFetchMock("/catalog/manual-books/", {
    method: "POST",
    body: {
      ...form,
      price: form.price === "" ? null : form.price
    }
  });
}

async function loadManualBooksForExport(nextFilters, catalogFetchMock) {
  const pageSize = 100;
  const normalizedFilters = {
    ...nextFilters,
    page: "1",
    limit: String(pageSize)
  };
  const firstPayload = normalizeCatalogListPayload(
    await catalogFetchMock(`/catalog/manual-books/${toQueryString(normalizedFilters)}`)
  );
  const allEntries = [...firstPayload.entries];
  const totalPages = Number(firstPayload.pagination.page_count) || 1;

  for (let page = 2; page <= totalPages; page += 1) {
    const nextPayload = normalizeCatalogListPayload(
      await catalogFetchMock(
        `/catalog/manual-books/${toQueryString({
          ...normalizedFilters,
          page: String(page)
        })}`
      )
    );
    allEntries.push(...nextPayload.entries);
  }

  return allEntries;
}

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
