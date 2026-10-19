import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { components } from "@/api/vendor/schema";
import { BookCard } from "@/components/book-card";
import { CatalogExportControls } from "@/components/catalog-export-controls";
import { CatalogFiltersForm } from "@/components/catalog-filters-form";
import { Icon } from "@/components/icon";
import { SiteNav, SiteNumber, SiteText } from "@/components/site-language";
import { catalogFilterKeys } from "@/lib/catalog-filters";
import { localizeMetadata } from "@/lib/metadata-language";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireReader } from "@/lib/workspace-session";
import { PhysicalListFilters } from "@/components/physical-list-filters";

type PhysicalBook = components["schemas"]["PublicBookDetail"];
type PhysicalBooks = { entries: PhysicalBook[]; pagination: { page_count: number; total_count: number; has_next: boolean; has_previous: boolean } };

export async function generateMetadata() { return localizeMetadata({ title: "কাগজের বই" }); }

export default async function PhysicalBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireReader("/physical-books/");
  const query = await searchParams, page = routePageNumber(query);
  const physicalKeys = ["writer", "translator", "editor", "publisher", "binding", "language"];
  const filters = Object.fromEntries(["q", ...catalogFilterKeys, ...physicalKeys].map(name => [name, queryValue(query, name)]));
  if (Object.values(filters).some(value => value.length > 255) || filters.q.length > 120) notFound();
  filters.record_type = "manual";
  const parameters = new URLSearchParams(filters);
  let books: PhysicalBooks;
  try { books = await sessionRequest<PhysicalBooks>(`catalog/physical-books/?${parameters}&page=${page}`); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  return <><header className="catalog-list-heading"><div><h1><SiteText>কাগজের বই</SiteText></h1>
    <p className="muted"><SiteText>আপনার অনুমতি পাওয়া কাগজের বইয়ের তালিকা।</SiteText></p></div>
    {session.workspaces.can_create_books && <Link className="button" href="/manage/books/new/?record_type=manual"><Icon name="plus" /><SiteText>কাগজের বই যোগ করুন</SiteText></Link>}</header>
    <CatalogFiltersForm key={parameters.toString()} pathname="/physical-books/" initial={filters} lockedRecordType="manual" hidden={Object.fromEntries(physicalKeys.map(key => [key, filters[key]]))} />
    <PhysicalListFilters filters={filters} />
    <CatalogExportControls filters={filters} scope="physical" />
    <p className="muted"><SiteNumber value={books.pagination.total_count} /> <SiteText>টি বই</SiteText></p>
    {books.entries.length ? <div className="book-grid">{books.entries.map(book => <div key={book.id}>
      <BookCard book={book} href={`/my-books/${encodeURIComponent(book.slug)}/`} />
      <p className="muted">{book.manual_publisher}{book.manual_publisher && book.manual_price !== null ? " · " : ""}{book.manual_price !== null ? `৳ ${book.manual_price}` : ""}</p>
      {session.workspaces.management_sections.includes("books") && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/`}><Icon name="edit" /><SiteText>তথ্য সম্পাদনা করুন</SiteText></Link>}
    </div>)}</div> : <section className="empty-state"><Icon name="books" /><h2><SiteText>এই তালিকায় কোনো বই পাওয়া যায়নি।</SiteText></h2>
      <p><SiteText>ফিল্টার বদলান। বই দেখার অনুমতি না থাকলে প্রশাসকের সঙ্গে যোগাযোগ করুন।</SiteText></p></section>}
    <SiteNav className="pagination" aria-label="কাগজের বইয়ের পাতা">
      {books.pagination.has_previous && <Link className="button button-quiet" href={`?${parameters}&page=${page - 1}`}><SiteText>আগের পাতা</SiteText></Link>}
      <span><SiteText>পাতা </SiteText><SiteNumber value={page} /></span>
      {books.pagination.has_next && <Link className="button" href={`?${parameters}&page=${page + 1}`}><SiteText>পরের পাতা</SiteText></Link>}
    </SiteNav></>;
}
