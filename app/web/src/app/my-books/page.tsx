import { currentBrowseFilters, retiredFilterRedirect } from "@/lib/browse-filters";
import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText, SiteNav } from "@/components/site-language";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { LibraryCollection } from "@/api/types";
import { ContinueReading } from "@/components/continue-reading";
import { BookResults } from "@/components/book-results";
import { CatalogExportControls } from "@/components/catalog-export-controls";
import { CatalogFiltersForm } from "@/components/catalog-filters-form";
import { catalogFilterKeys } from "@/lib/catalog-filters";
import { requireReader } from "@/lib/workspace-session";
import { ManagedBooksShortcut } from "@/components/managed-books-shortcut";
import { Icon, type IconName } from "@/components/icon";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";
import "./library.css";
import { CatalogPagination } from "@/components/catalog-pagination";

export async function generateMetadata() { return localizeMetadata({ title: "আমার বই" }); }
const views = { all: "আমার সব বই", owned: "আমার সংগ্রহ", saved: "সংরক্ষিত", recent: "সাম্প্রতিক পাঠ", granted: "অনুমতি পাওয়া বই" };
const viewIcons: Record<string, IconName> = { all: "books", owned: "read", saved: "bookmark", recent: "refresh", granted: "people" };

export default async function MyBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireReader("/my-books/");
  const parameters = await searchParams, page = catalogPageNumber(parameters), query = queryValue(parameters, "q"), view = queryValue(parameters, "view") || "all";
  const destination = retiredFilterRedirect("/my-books/", parameters);
  if (destination) redirect(destination);
  if (!Object.hasOwn(views, view) || query.length > 120) notFound();
  const selectedFilters = Object.fromEntries(catalogFilterKeys.map((name) => [name, queryValue(parameters, name)]));
  if (Object.values(selectedFilters).some((value) => value.length > 255)) notFound();
  if (!selectedFilters.record_type) selectedFilters.record_type = "all";
  const filtered = !!query || Object.entries(selectedFilters).some(([name, value]) => name !== "sort" && !!value && value !== "all");
  const filters = new URLSearchParams({ ...selectedFilters, view, q: query });
  let books: LibraryCollection | null = null;
  try { books = await sessionRequest<LibraryCollection>(`me/books/?${filters}&page=${page}`); }
  catch (error) { if (!(error instanceof APIError && error.status === 400)) throw error; }
  if (books && page > 1 && !books.entries.length) notFound();
  return <section className="personal-library"><header className="page-title"><h1><SiteText>{"আমার বই"}</SiteText></h1></header>
    <ManagedBooksShortcut />
    {view === "all" && !filtered && page === 1 && <ContinueReading />}
    <SiteNav className="workspace-nav personal-library-tabs" aria-label="ব্যক্তিগত বইয়ের তালিকা">{Object.entries(views).map(([value, label]) => <Link href={`?${new URLSearchParams(currentBrowseFilters({ ...selectedFilters, q: query, view: value }))}`} key={value} aria-current={view === value ? "page" : undefined}><Icon name={viewIcons[value]} /><SiteText>{label}</SiteText></Link>)}</SiteNav>
    <CatalogFiltersForm key={filters.toString()} pathname="/my-books/" initial={{ ...selectedFilters, q: query }} hidden={{ view }} />
    {!books && <p role="alert" className="field-error"><SiteText>{"অক্ষর বা সংখ্যা দিয়ে বইয়ের নাম খুঁজুন।"}</SiteText></p>}
    {books?.entries.length ? <BookResults books={books.entries} library /> : books && <section className="empty-state"><h2><SiteText>{"এই তালিকা এখন খালি"}</SiteText></h2>
      <p><SiteText>{filtered ? "ফিল্টার বদলে বা কম শর্ত দিয়ে আবার খুঁজুন।" : "বইয়ের পাতা খুলে আমার বইয়ে যোগ করুন বাটনে চাপুন। যোগ করা বই এখানে পাবেন।"}</SiteText></p><Link className="text-link" href="/catalog/"><Icon name="plus" /><SiteText>{"বই খুঁজুন →"}</SiteText></Link></section>}
    {books && <CatalogPagination pathname="/my-books/" page={page} hasMore={books.has_more} totalPages={books.pagination?.page_count} filters={{ ...selectedFilters, view, q: query }} label="আমার বইয়ের পাতা" />}
    <CatalogExportControls scope="library" filters={{ ...selectedFilters, q: query, view }} />
  </section>;
}
