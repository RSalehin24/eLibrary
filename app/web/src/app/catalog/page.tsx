import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { CatalogSearch } from "@/components/catalog-search";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";
import { APIError } from "@/api/http";

type SearchParameters = Promise<RouteQuery>;

export async function generateMetadata({ searchParams }: { searchParams: SearchParameters }): Promise<Metadata> {
  const parameters = await searchParams;
  const q = queryValue(parameters, "q"), page = catalogPageNumber(parameters);
  return { title: q ? `“${q}” খুঁজুন` : "বইয়ের পাঠাগার",
    robots: { index: !q && Object.keys(parameters).every((name) => name === "page"), follow: true },
    alternates: { canonical: `/catalog/${q || page > 1 ? `?${new URLSearchParams({ ...(q ? { q } : {}), ...(page > 1 ? { page: String(page) } : {}) })}` : ""}` },
  };
}

export default async function CatalogPage({ searchParams }: { searchParams: SearchParameters }) {
  const queryParameters = await searchParams;
  const q = queryValue(queryParameters, "q");
  const pageNumber = catalogPageNumber(queryParameters);
  if (q.length > 120) notFound();
  const parameters = new URLSearchParams({ q, page: String(pageNumber) });
  let books: BookCollection;
  try { books = await publicRequest<BookCollection>(`catalog/books/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 400) notFound(); throw error; }
  if (pageNumber > 1 && !books.entries.length) notFound();
  return <><header className="page-title"><p className="eyebrow">বাংলা বইয়ের সন্ধানে</p><h1>বইয়ের পাঠাগার</h1>
    <p className="muted">বইয়ের নাম বা লেখকের নাম দিয়ে খুঁজুন।</p><Link className="text-link" href="/collections/">সম্পাদকের নির্বাচন দেখুন →</Link></header>
    <CatalogSearch key={`${q}:${pageNumber}`} initialQuery={q} initialBooks={books} page={pageNumber} />
    </>;
}
