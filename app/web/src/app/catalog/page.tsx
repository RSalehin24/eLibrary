import { retiredFilterRedirect } from "@/lib/browse-filters";
import { SiteText } from "@/components/site-language";
import { localizeMetadata } from "@/lib/metadata-language";
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { publicRequest, sessionRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { catalogFilterKeys, catalogNeedsAccount } from "@/lib/catalog-filters";
import { CatalogSearch } from "@/components/catalog-search";
import { CatalogBrowseNav } from "@/components/catalog-browse-nav";
import { ManagedBooksShortcut } from "@/components/managed-books-shortcut";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";
import { APIError } from "@/api/http";

type SearchParameters = Promise<RouteQuery>;

export async function generateMetadata({ searchParams }: { searchParams: SearchParameters }): Promise<Metadata> {
  const parameters = await searchParams;
  const q = queryValue(parameters, "q"), page = catalogPageNumber(parameters);
  return localizeMetadata({ title: q ? `“${q}”` : "বইয়ের পাঠাগার",
    robots: { index: !q && Object.keys(parameters).every((name) => name === "page"), follow: true },
    alternates: { canonical: `/catalog/${q || page > 1 ? `?${new URLSearchParams({ ...(q ? { q } : {}), ...(page > 1 ? { page: String(page) } : {}) })}` : ""}` },
  });
}

export default async function CatalogPage({ searchParams }: { searchParams: SearchParameters }) {
  const queryParameters = await searchParams;
  const destination = retiredFilterRedirect("/catalog/", queryParameters);
  if (destination) redirect(destination);
  const q = queryValue(queryParameters, "q");
  const pageNumber = catalogPageNumber(queryParameters);
  if (q.length > 120) notFound();
  const filters = Object.fromEntries(catalogFilterKeys.map((name) => [name, queryValue(queryParameters, name)]));
  if (Object.values(filters).some((value) => value.length > 255)) notFound();
  if (!filters.record_type) filters.record_type = "all";
  const parameters = new URLSearchParams({ ...filters, q, page: String(pageNumber) });
  let books: BookCollection;
  try { books = await (catalogNeedsAccount(filters) ? sessionRequest<BookCollection> : publicRequest<BookCollection>)(`catalog/books/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 400) notFound(); throw error; }
  if (pageNumber > 1 && !books.entries.length) notFound();
  return <section className="catalog-page"><header className="page-title catalog-page-title"><h1><SiteText>{"সব বই"}</SiteText></h1>
    </header><CatalogBrowseNav current="/catalog/" />
    <ManagedBooksShortcut /><CatalogSearch key={`${parameters}`} initialFilters={filters} initialQuery={q} initialBooks={books} page={pageNumber} />
    </section>;
}
