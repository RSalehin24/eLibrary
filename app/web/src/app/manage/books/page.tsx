import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedBooks } from "@/api/types";
import { localizeMetadata } from "@/lib/metadata-language";
import { requireManagement } from "@/lib/workspace-session";
import { catalogStateLabel } from "@/lib/catalog-state";
import { entityFilters } from "@/lib/catalog-entity";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { AdminNumber, AdminText } from "@/components/admin-language";
import { AdminPagination } from "@/components/admin-pagination";
import { BookCard } from "@/components/book-card";
import { CatalogFiltersForm } from "@/components/catalog-filters-form";
import { CatalogExportControls } from "@/components/catalog-export-controls";
import { catalogFilterKeys } from "@/lib/catalog-filters";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ title: "সব বই" }); }

export default async function ManagedBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireManagement("books");
  const query = await searchParams, page = routePageNumber(query);
  const filter = new URLSearchParams();
  for (const key of ["q", ...catalogFilterKeys, "label"]) {
    const value = queryValue(query, key);
    if (value.length > (key === "q" ? 120 : 255)) notFound();
    if (value) filter.set(key, value);
  }
  let books: ManagedBooks;
  try { books = await sessionRequest<ManagedBooks>(`manage/books/?${filter}&page=${page}`); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  const filtered = [...filter.keys()].some(key => key !== "q");
  return <><header className="catalog-list-heading"><div><h1>{filter.get("label") || <AdminText>{"সব বই"}</AdminText>}</h1>
    <p className="muted"><AdminText>{"খসড়া, প্রস্তুত ও প্রকাশিত সব বই এখানে পাবেন। বই খুলে পড়ুন, ফাইল নামান বা তথ্য সম্পাদনা করুন।"}</AdminText></p></div>
    <div className="editorial-actions">{session.workspaces.can_create_books && <Link className="button" href="/manage/books/new/"><Icon name="plus" /><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></Link>}
      {session.workspaces.management_sections.includes("sources") && <Link className="button button-quiet" href="/manage/sources/"><Icon name="source" /><AdminText>{"উৎস থেকে বই আনুন"}</AdminText></Link>}</div></header>
    <CatalogFiltersForm key={filter.toString()} pathname="/manage/books/" initial={Object.fromEntries(filter)} />
    <CatalogExportControls scope="managed" filters={Object.fromEntries(filter)} />
    {filtered && <p className="catalog-filter-summary"><AdminText>{"নির্বাচিত লেখক, বিভাগ বা সংগ্রহের বই দেখানো হচ্ছে।"}</AdminText> <Link className="button button-quiet" href="/manage/books/"><Icon name="books" /><AdminText>{"সব বই দেখুন"}</AdminText></Link></p>}
    <p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={books.pagination.total_count} /><AdminText>{"টি বই"}</AdminText></p>
    <ul className="managed-book-grid">{books.entries.map(book => <li key={book.id}><span className="status-label"><AdminText>{catalogStateLabel(book.state)}</AdminText></span>
      <BookCard book={book} href={`/manage/books/${encodeURIComponent(book.slug)}/`} actionLabel="বই খুলুন" entityHref={(kind, slug, role) => `/manage/books/?${new URLSearchParams({ [entityFilters[kind]]: slug, ...(role ? { contributor_role: role } : {}) })}`} /></li>)}</ul>
    {!books.entries.length && <section className="empty-state"><Icon name="books" /><h2><AdminText>{filter.size ? "এই খোঁজে কোনো বই পাওয়া যায়নি।" : "এখনও কোনো বই যোগ করা হয়নি।"}</AdminText></h2>
      {filter.size ? !filtered && <Link className="button button-quiet" href="/manage/books/"><Icon name="refresh" /><AdminText>{"সব বই দেখুন"}</AdminText></Link> : <p><AdminText>{"বই তৈরি করুন অথবা নিজের EPUB যোগ করুন।"}</AdminText></p>}</section>}
    <AdminPagination pagination={books.pagination} filter={filter.toString()} label="পরিচালনার তালিকার পাতা" /></>;
}
