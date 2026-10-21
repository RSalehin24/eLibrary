import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { CatalogPagination } from "@/components/catalog-pagination";
import Link from "next/link";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { BookCard } from "@/components/book-card";
import { getPublicBook } from "@/lib/public-book";
import { routeSlug } from "@/lib/route-slug";
import { catalogPageNumber, type RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "সম্পর্কিত সংস্করণ", robots: { index: false, follow: true } }); }

export default async function EditionsPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<RouteQuery> }) {
  const book = await getPublicBook(routeSlug((await params).slug)), page = catalogPageNumber(await searchParams);
  const editions = await publicRequest<BookCollection>(`catalog/books/${encodeURIComponent(book.slug)}/editions/?page=${page}`);
  return <><Link className="text-link" href={`/books/${encodeURIComponent(book.slug)}/`}><SiteText>{"← বইয়ের পরিচিতিতে ফিরুন"}</SiteText></Link><h1>{book.title}<SiteText>{": অন্য সংস্করণ"}</SiteText></h1>
    <div className="book-grid">{editions.entries.map((entry) => <BookCard book={entry} key={entry.id} />)}</div>
    {!editions.entries.length && <p><SiteText>{"অন্য কোনো প্রকাশিত সংস্করণ নেই।"}</SiteText></p>}
    <CatalogPagination pathname={`/books/${encodeURIComponent(book.slug)}/editions/`} page={page} hasMore={editions.has_more} totalPages={editions.pagination?.page_count} label="সংস্করণের পাতা" /></>;
}
