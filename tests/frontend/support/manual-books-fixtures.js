import {
  MANUAL_BOOKS_EXPORT_STORAGE_KEY,
  emptyManualBookForm,
  defaultManualBookFilters,
  manualBookFilterFields,
  manualBookToolbarFields,
  manualBookSortOptions,
} from "../../../app/frontend/src/features/manual-books/manualBookFilters.js";

export function toQueryString(params) {
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

export function normalizeCatalogListPayload(payload) {
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

export async function loadManualBookOptions(catalogFetchMock) {
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

export function mergeContributorSuggestions(payloads) {
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

export async function createManualBook(form, catalogFetchMock) {
  return catalogFetchMock("/catalog/manual-books/", {
    method: "POST",
    body: {
      ...form,
      price: form.price === "" ? null : form.price
    }
  });
}

export async function loadManualBooksForExport(nextFilters, catalogFetchMock) {
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
