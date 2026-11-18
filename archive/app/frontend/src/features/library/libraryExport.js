import { catalogFetch } from "../../api/catalog";
import { normalizeBookPayload } from "../../utils/catalogBooks";
import { toQueryString } from "../../utils/query";

export async function loadLibraryBooksForExport(nextFilters) {
  const pageSize = 100;
  const normalizedFilters = {
    ...nextFilters,
    page: "1",
    limit: String(pageSize)
  };
  const firstPayload = normalizeBookPayload(
    await catalogFetch(`/catalog/books/${toQueryString(normalizedFilters)}`)
  );
  const allEntries = [...firstPayload.entries];
  const totalPages = Number(firstPayload.pagination.page_count) || 1;

  for (let page = 2; page <= totalPages; page += 1) {
    const nextPayload = normalizeBookPayload(
      await catalogFetch(
        `/catalog/books/${toQueryString({
          ...normalizedFilters,
          page: String(page)
        })}`
      )
    );
    allEntries.push(...nextPayload.entries);
  }

  return allEntries;
}
