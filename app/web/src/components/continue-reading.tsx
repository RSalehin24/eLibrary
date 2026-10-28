import Link from "next/link";
import { sessionRequest } from "@/api/server";
import type { LibraryCollection } from "@/api/types";
import { BookCover } from "./book-cover";
import { SiteNumber, SiteText } from "./site-language";
import { ContinueReadingAction } from "./continue-reading-action";

const maximumContinueReadingBooks = 3;

export async function ContinueReading() {
  const recent = await sessionRequest<LibraryCollection>("me/books/?view=recent");
  const entries = recent.entries.filter(book => book.progress_percent !== null && book.progress_percent < 100).slice(0, maximumContinueReadingBooks);
  if (!entries.length) return null;
  return <section className="continue-reading" aria-labelledby="continue-reading-heading"><h2 id="continue-reading-heading"><SiteText>পড়া চালিয়ে যান</SiteText></h2><div className="continue-reading-list">{entries.map(book => <article key={book.id}>
    <BookCover title={book.title} coverUrl={book.cover_url} /><div><h3><Link href={`/my-books/${encodeURIComponent(book.slug)}/?view=recent`}>{book.title}</Link></h3><p className="muted"><SiteNumber value={Math.round(book.progress_percent ?? 0)} />% <SiteText>পড়া হয়েছে</SiteText></p><ContinueReadingAction slug={book.slug} /></div>
  </article>)}</div></section>;
}
