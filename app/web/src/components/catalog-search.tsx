"use client";

import { SiteText } from "@/components/site-language";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { readSession, searchBooks } from "@/api/catalog";
import type { BookCollection } from "@/api/types";
import { BookResults } from "./book-results";
import { CatalogExportControls } from "./catalog-export-controls";
import { CatalogFiltersForm } from "./catalog-filters-form";
import { catalogFilterQuery, catalogNeedsAccount, type CatalogFilters } from "@/lib/catalog-filters";
import { CatalogPagination } from "./catalog-pagination";
import { useDebouncedQuery } from "@/lib/debounced-query";

type SearchProps = { initialQuery: string; initialBooks: BookCollection; page: number; initialFilters?: CatalogFilters };

export function CatalogSearch({ initialQuery, initialBooks, page, initialFilters = {} }: SearchProps) {
  const initial = catalogFilterQuery({ record_type: "all", ...initialFilters, q: initialQuery });
  const [query, setQuery] = useState(initial);
  const debounced = useDebouncedQuery(query);
  const filters = Object.fromEntries(new URLSearchParams(debounced));
  const personal = catalogNeedsAccount(filters);
  const account = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal), enabled: personal });
  const hasFilters = Object.entries(filters).some(([name, value]) => !["sort", "record_type"].includes(name) && !!value || name === "record_type" && value !== "all");
  const results = useQuery({
    queryKey: [...(personal ? ["private", "catalog-books", account.data?.user?.id] : ["public", "books"]), debounced, debounced === initial ? page : 1],
    queryFn: ({ signal }) => searchBooks({ query: filters.q ?? "", filters, page: debounced === initial ? page : 1 }, signal),
    enabled: !personal || account.isFetched,
    initialData: debounced === initial ? initialBooks : undefined,
    placeholderData: keepPreviousData,
  });
  const currentPage = debounced === initial ? page : 1;
  return <>
    <CatalogFiltersForm pathname="/catalog/" initial={{ ...initialFilters, q: initialQuery }} onChange={(values) => setQuery(catalogFilterQuery(values))} />
    <div aria-live="polite">{results.isFetching && <p className="muted"><SiteText>{"বই খোঁজা হচ্ছে…"}</SiteText></p>}
      {results.error && <p className="notice" role="alert"><SiteText>{"বই খোঁজা যায়নি। আবার চেষ্টা করুন।"}</SiteText> <button type="button" className="button button-quiet" onClick={() => void results.refetch()}><SiteText>আবার চেষ্টা করুন</SiteText></button></p>}</div>
    {results.data?.entries.length ? <BookResults books={results.data.entries} busy={results.isFetching} />
      : results.data && <div className="empty-state"><h2><SiteText>{hasFilters ? "কোনো বই পাওয়া যায়নি" : "এখনও কোনো বই প্রকাশিত হয়নি"}</SiteText></h2><p><SiteText>{hasFilters ? "ফিল্টার বদলে বা কম শর্ত দিয়ে আবার খুঁজুন।" : "প্রকাশিত বই এখানে দেখা যাবে। ব্যক্তিগত বই পাবেন আমার বই পাতায়।"}</SiteText></p></div>}
    {results.data && !results.isPlaceholderData && <CatalogPagination pathname="/catalog/" page={currentPage} hasMore={results.data.has_more} totalPages={results.data.pagination?.page_count} query={filters.q ?? ""} filters={filters} />}
    <CatalogExportControls filters={filters} />
  </>;
}
