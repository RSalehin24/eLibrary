import Link from "next/link";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { BookCard } from "@/components/book-card";
import { StructuredData } from "@/components/structured-data";
import { canonicalURL, siteName } from "@/lib/site";

export const metadata = { alternates: { canonical: "/" } };

export default async function HomePage() {
  const books = await publicRequest<BookCollection>("catalog/books/?limit=4");
  return <>
    <StructuredData data={{ "@context": "https://schema.org", "@type": "Organization", name: siteName, url: canonicalURL("/") }} />
    <section className="hero"><div>
      <p className="eyebrow">বিশ্বজুড়ে বাংলা পাঠকের পাঠাগার</p>
      <h1>বইয়ের পাতায়<br />ফিরে আসুন।</h1>
      <p className="hero-description">চেনা লেখক, নতুন গল্প। বাংলায় বই খুঁজুন, বইয়ের পরিচিতি জানুন, আর নিজের পাঠের জায়গা গড়ে তুলুন।</p>
      <form action="/catalog/" className="search-form" role="search">
        <label className="visually-hidden" htmlFor="home-search">বই বা লেখকের নাম</label>
        <input id="home-search" name="q" placeholder="বই বা লেখকের নাম লিখুন" maxLength={120} />
        <button type="submit" className="button">খুঁজুন</button>
      </form>
      <Link className="text-link" href="/catalog/">সব বই দেখুন <span aria-hidden="true">→</span></Link>
    </div><div className="hero-art" aria-hidden="true"><div className="shelf-book"><span>গল্প</span>
      <svg className="cover-motif" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="24" stroke="currentColor" strokeWidth=".8" /><path d="M32 12v40M12 32h40M18 18l28 28M18 46l28-28" stroke="currentColor" strokeWidth=".8" /><circle cx="32" cy="32" r="12" stroke="currentColor" strokeWidth=".8" /></svg>
      <small>বাংলা সাহিত্য</small></div><div className="shelf-book second"><span>পাঠের<br />পৃথিবী</span><small>বাংলা পাঠাগার</small></div>
      <span className="hero-caption">একটি বই। অনেক পৃথিবী।</span></div></section>
    <section aria-labelledby="new-books"><div className="section-heading"><div><p className="eyebrow">পাঠ শুরু হোক</p>
      <h2 id="new-books">প্রকাশিত বই</h2></div><Link className="text-link" href="/catalog/">পাঠাগার দেখুন →</Link></div>
      {books.entries.length ? <div className="book-grid">{books.entries.map((book) => <BookCard key={book.id} book={book} />)}</div>
        : <div className="empty-state"><h3>প্রকাশিত বই শিগগিরই এখানে দেখা যাবে</h3><p>পর্যালোচনা শেষে বইয়ের পরিচিতি পাঠাগারে প্রকাশ করা হয়।</p></div>}
    </section>
    <section className="reading-banner"><div><p className="eyebrow">আপনার পাঠের সঙ্গী</p><h2>নিজের পাঠাগার, নিজের মতো।</h2>
      <p>পড়ার অবস্থান, বুকমার্ক ও নোট এক জায়গায় রাখুন।</p></div><Link className="button" href="/my-books/">আমার বইয়ে যান</Link></section>
  </>;
}
