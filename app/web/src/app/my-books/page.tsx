import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { LibraryCollection } from "@/api/types";
import { BookCard } from "@/components/book-card";
import { requireReader } from "@/lib/workspace-session";
import { bengaliNumber } from "@/lib/site";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";

export const metadata = { title: "আমার বই" };
const views = { owned: "আমার সংগ্রহ", saved: "সংরক্ষিত", recent: "সাম্প্রতিক পাঠ", granted: "অনুমতি পাওয়া বই" };

export default async function MyBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireReader("/my-books/");
  const parameters = await searchParams, page = catalogPageNumber(parameters), query = queryValue(parameters, "q"), view = queryValue(parameters, "view") || "owned";
  if (!Object.hasOwn(views, view) || query.length > 120) notFound();
  const filters = new URLSearchParams({ view, q: query });
  let books: LibraryCollection | null = null;
  try { books = await sessionRequest<LibraryCollection>(`me/books/?${filters}&page=${page}`); }
  catch (error) { if (!(error instanceof APIError && error.status === 400)) throw error; }
  const pageURL = (number: number) => `?${filters}&page=${number}`;
  return <><p className="eyebrow">আপনার ব্যক্তিগত পাঠাগার</p><h1>আমার বই</h1>
    <nav className="workspace-nav" aria-label="ব্যক্তিগত বইয়ের তালিকা">{Object.entries(views).map(([value, label]) => <Link href={`?view=${value}`} key={value} aria-current={view === value ? "page" : undefined}>{label}</Link>)}</nav>
    <form className="catalog-search" role="search"><input type="hidden" name="view" value={view} /><label htmlFor="library-query">নিজের তালিকায় বই খুঁজুন</label><div className="search-row"><input id="library-query" name="q" maxLength={120} defaultValue={query} /><button className="button">খুঁজুন</button></div></form>
    {!books && <p role="alert" className="field-error">অক্ষর বা সংখ্যা দিয়ে বইয়ের নাম খুঁজুন।</p>}
    {books?.entries.length ? <div className="book-grid">{books.entries.map((book) => <div key={book.id}>
      <BookCard book={book} href={`/my-books/${encodeURIComponent(book.slug)}/`} />
      {book.progress_percent !== null && <p className="muted">পড়া হয়েছে {bengaliNumber(book.progress_percent)}%</p>}
    </div>)}</div> : books && <section className="empty-state"><h2>এই তালিকা এখন খালি</h2>
      <p>আপনার সংগ্রহ, সংরক্ষিত বই, সাম্প্রতিক পাঠ ও বর্তমান অনুমতির বই আলাদা তালিকায় দেখা যাবে।</p><Link className="text-link" href="/catalog/">বই খুঁজুন →</Link></section>}
    {books && <nav className="pagination" aria-label="আমার বইয়ের পাতা">
      {page > 1 && <Link className="button button-quiet" href={pageURL(page-1)}>আগের পাতা</Link>}
      <span>পাতা {bengaliNumber(page)}</span>
      {books.has_more && <Link className="button" href={pageURL(page+1)}>পরের পাতা</Link>}
    </nav>}</>;
}
