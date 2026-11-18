import { catalogFetch } from "../../api/catalog";
import { normalizeCatalogListPayload } from "../../utils/catalogBooks";
import { toQueryString } from "../../utils/query";

export async function loadManualBooksForExport(nextFilters) {
  const pageSize = 100;
  const normalizedFilters = {
    ...nextFilters,
    page: "1",
    limit: String(pageSize)
  };
  const firstPayload = normalizeCatalogListPayload(
    await catalogFetch(`/catalog/manual-books/${toQueryString(normalizedFilters)}`)
  );
  const allEntries = [...firstPayload.entries];
  const totalPages = Number(firstPayload.pagination.page_count) || 1;

  for (let page = 2; page <= totalPages; page += 1) {
    const nextPayload = normalizeCatalogListPayload(
      await catalogFetch(
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
