import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText, SiteNav, SiteNumber } from "@/components/site-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { LibraryCollection } from "@/api/types";
import { BookCard } from "@/components/book-card";
import { requireReader } from "@/lib/workspace-session";
import { ManagedBooksShortcut } from "@/components/managed-books-shortcut";
import { Icon, type IconName } from "@/components/icon";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "আমার বই" }); }
const views = { all: "আমার সব বই", owned: "আমার সংগ্রহ", saved: "সংরক্ষিত", recent: "সাম্প্রতিক পাঠ", granted: "অনুমতি পাওয়া বই" };
const viewIcons: Record<string, IconName> = { all: "books", owned: "read", saved: "bookmark", recent: "refresh", granted: "people" };

export default async function MyBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireReader("/my-books/");
  const parameters = await searchParams, page = catalogPageNumber(parameters), query = queryValue(parameters, "q"), view = queryValue(parameters, "view") || "all";
  if (!Object.hasOwn(views, view) || query.length > 120) notFound();
  const filters = new URLSearchParams({ view, q: query });
  let books: LibraryCollection | null = null;
  try { books = await sessionRequest<LibraryCollection>(`me/books/?${filters}&page=${page}`); }
  catch (error) { if (!(error instanceof APIError && error.status === 400)) throw error; }
  const pageURL = (number: number) => `?${filters}&page=${number}`;
  return <><p className="eyebrow"><SiteText>{"আপনার ব্যক্তিগত পাঠাগার"}</SiteText></p><h1><SiteText>{"আমার বই"}</SiteText></h1>
    <ManagedBooksShortcut />
    <SiteNav className="workspace-nav" aria-label="ব্যক্তিগত বইয়ের তালিকা">{Object.entries(views).map(([value, label]) => <Link href={`?view=${value}`} key={value} aria-current={view === value ? "page" : undefined}><Icon name={viewIcons[value]} /><SiteText>{label}</SiteText></Link>)}</SiteNav>
    <form className="catalog-search" role="search"><input type="hidden" name="view" value={view} /><label htmlFor="library-query"><SiteText>{"নিজের তালিকায় বই খুঁজুন"}</SiteText></label><div className="search-row"><input id="library-query" name="q" maxLength={120} defaultValue={query} /><button className="button"><SiteText>{"খুঁজুন"}</SiteText></button></div></form>
    {!books && <p role="alert" className="field-error"><SiteText>{"অক্ষর বা সংখ্যা দিয়ে বইয়ের নাম খুঁজুন।"}</SiteText></p>}
    {books?.entries.length ? <div className="book-grid">{books.entries.map((book) => <div key={book.id}>
      <BookCard book={book} href={`/my-books/${encodeURIComponent(book.slug)}/`} />
      {book.progress_percent !== null && <p className="muted"><SiteText>{"পড়া হয়েছে "}</SiteText><SiteNumber value={book.progress_percent} />%</p>}
    </div>)}</div> : books && <section className="empty-state"><h2><SiteText>{"এই তালিকা এখন খালি"}</SiteText></h2>
      <p><SiteText>{"বইয়ের পাতা খুলে আমার বইয়ে যোগ করুন বাটনে চাপুন। যোগ করা বই এখানে পাবেন।"}</SiteText></p><Link className="text-link" href="/catalog/"><Icon name="plus" /><SiteText>{"বই খুঁজুন →"}</SiteText></Link></section>}
    {books && <SiteNav className="pagination" aria-label="আমার বইয়ের পাতা">
      {page > 1 && <Link className="button button-quiet" href={pageURL(page-1)}><SiteText>{"আগের পাতা"}</SiteText></Link>}
      <span><SiteText>{"পাতা "}</SiteText><SiteNumber value={page} /></span>
      {books.has_more && <Link className="button" href={pageURL(page+1)}><SiteText>{"পরের পাতা"}</SiteText></Link>}
    </SiteNav>}</>;
}
