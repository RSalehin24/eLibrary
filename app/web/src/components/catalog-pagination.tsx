import { NumberedPagination } from "./numbered-pagination";
import { currentBrowseFilters } from "@/lib/browse-filters";

type PaginationProps = { pathname: string; page: number; hasMore: boolean; totalPages?: number; query?: string; filters?: Readonly<Record<string, string>>; label?: string };

export function CatalogPagination({ pathname, page, hasMore, totalPages, query, filters, label = "বইয়ের তালিকার পাতা" }: PaginationProps) {
  return <NumberedPagination pathname={pathname} page={page} totalPages={totalPages} hasNext={hasMore} query={new URLSearchParams(currentBrowseFilters({ ...filters, ...(query ? { q: query } : {}) })).toString()} label={label} />;
}
