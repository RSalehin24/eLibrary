"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useState } from "react";
import { searchBooks } from "@/api/catalog";
import type { BookCollection } from "@/api/types";
import { BookCard } from "./book-card";
import { CatalogPagination } from "./catalog-pagination";
import { useDebouncedQuery } from "@/lib/debounced-query";

type SearchProps = { initialQuery: string; initialBooks: BookCollection; page: number };

export function CatalogSearch({ initialQuery, initialBooks, page }: SearchProps) {
  const [query, setQuery] = useState(initialQuery);
  const debounced = useDebouncedQuery(query);
  const results = useQuery({
    queryKey: ["public", "books", debounced, debounced === initialQuery ? page : 1],
    queryFn: ({ signal }) => searchBooks({ query: debounced, page: debounced === initialQuery ? page : 1 }, signal),
    initialData: debounced === initialQuery ? initialBooks : undefined,
    placeholderData: keepPreviousData,
  });
  const currentPage = debounced === initialQuery ? page : 1;
  return <>
    <form action="/catalog/" className="search-form" role="search">
      <label className="visually-hidden" htmlFor="catalog-query">বই বা লেখকের নাম</label>
      <input id="catalog-query" name="q" value={query} maxLength={120}
        onChange={(event) => setQuery(event.target.value)} placeholder="বই বা লেখকের নাম লিখুন" />
      <button className="button" type="submit">খুঁজুন</button>
    </form>
    <div aria-live="polite">{results.isFetching && <p className="muted">বই খোঁজা হচ্ছে…</p>}
      {results.error && <p className="notice" role="alert">বই খোঁজা যায়নি। আবার চেষ্টা করুন।</p>}</div>
    {results.data?.entries.length ? <div className="book-grid" aria-busy={results.isFetching}>
      {results.data.entries.map((book) => <BookCard key={book.id} book={book} />)}</div>
      : <div className="empty-state"><h2>কোনো বই পাওয়া যায়নি</h2><p>অন্য নাম বা ছোট একটি শব্দ দিয়ে খুঁজুন।</p></div>}
    {results.data && !results.isPlaceholderData && <CatalogPagination pathname="/catalog/" page={currentPage} hasMore={results.data.has_more} query={debounced} />}
  </>;
}
