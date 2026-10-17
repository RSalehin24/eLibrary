import { SiteText } from "@/components/site-language";
import { localizeMetadata } from "@/lib/metadata-language";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
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
  const q = queryValue(queryParameters, "q");
  const pageNumber = catalogPageNumber(queryParameters);
  if (q.length > 120) notFound();
  const parameters = new URLSearchParams({ q, page: String(pageNumber) });
  let books: BookCollection;
  try { books = await publicRequest<BookCollection>(`catalog/books/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 400) notFound(); throw error; }
  if (pageNumber > 1 && !books.entries.length) notFound();
  return <><CatalogBrowseNav current="/catalog/" /><header className="page-title"><p className="eyebrow"><SiteText>{"বাংলা বইয়ের সন্ধানে"}</SiteText></p><h1><SiteText>{"বইয়ের পাঠাগার"}</SiteText></h1>
    <p className="muted"><SiteText>{"বইয়ের নাম বা লেখকের নাম দিয়ে খুঁজুন।"}</SiteText></p><Link className="text-link" href="/collections/"><SiteText>{"সম্পাদকের নির্বাচন দেখুন →"}</SiteText></Link></header>
    <ManagedBooksShortcut /><CatalogSearch key={`${q}:${pageNumber}`} initialQuery={q} initialBooks={books} page={pageNumber} />
    </>;
}
