import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { workspaceHome, workspaceViewCookie } from "@/lib/workspace-view";
import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText, SiteInput } from "@/components/site-language";
import Link from "next/link";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { BookCard } from "@/components/book-card";
import { StructuredData } from "@/components/structured-data";
import { canonicalURL, siteName } from "@/lib/site";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ alternates: { canonical: "/" } }); }

export default async function HomePage() {
  const session = await getWorkspaceSession();
  if (session.authenticated) redirect(workspaceHome(session, (await cookies()).get(workspaceViewCookie)?.value));
  const books = await publicRequest<BookCollection>("catalog/books/?limit=4");
  return <>
    <StructuredData data={{ "@context": "https://schema.org", "@type": "Organization", name: siteName, url: canonicalURL("/") }} />
    <section className="hero"><div>
      <p className="eyebrow"><SiteText>{"বাংলা পাঠাগার"}</SiteText></p>
      <h1><SiteText>আপনার পরের বইটি খুঁজুন</SiteText></h1>
      <p className="hero-description"><SiteText>বই খুঁজুন, পড়ুন, আর আপনার নোটগুলো এক জায়গায় রাখুন।</SiteText></p>
      <form action="/catalog/" className="search-form" role="search">
        <label className="visually-hidden" htmlFor="home-search"><SiteText>{"বই বা লেখকের নাম"}</SiteText></label>
        <SiteInput id="home-search" name="q" placeholder="বই বা লেখকের নাম লিখুন" maxLength={120} />
        <button type="submit" className="button"><SiteText>{"খুঁজুন"}</SiteText></button>
      </form>
      <Link className="text-link" href="/catalog/"><SiteText>{"সব বই দেখুন "}</SiteText><span aria-hidden="true">→</span></Link>
    </div><aside className="home-reading-panel"><p className="eyebrow"><SiteText>আপনার পাঠাগার</SiteText></p><h2><SiteText>বই, পড়া আর নোট—এক জায়গায়</SiteText></h2>
      <Link href="/my-books/"><Icon name="books" size={22} /><span><strong><SiteText>আমার বই</SiteText></strong><small><SiteText>সংরক্ষিত বই থেকে আবার পড়া শুরু করুন।</SiteText></small></span><Icon name="arrow" /></Link>
      <Link href="/notes/"><Icon name="source" size={22} /><span><strong><SiteText>আমার নোট</SiteText></strong><small><SiteText>বুকমার্ক, নোট ও পছন্দের উদ্ধৃতি দেখুন।</SiteText></small></span><Icon name="arrow" /></Link>
      <Link href="/catalog/"><Icon name="search" size={22} /><span><strong><SiteText>সব বই দেখুন</SiteText></strong><small><SiteText>নাম বা লেখক দিয়ে বই খুঁজুন।</SiteText></small></span><Icon name="arrow" /></Link>
    </aside></section>
    <section aria-labelledby="new-books"><div className="section-heading"><div><p className="eyebrow"><SiteText>{"পাঠ শুরু হোক"}</SiteText></p>
      <h2 id="new-books"><SiteText>{"প্রকাশিত বই"}</SiteText></h2></div><Link className="text-link" href="/catalog/"><SiteText>{"পাঠাগার দেখুন →"}</SiteText></Link></div>
      {books.entries.length ? <div className="book-grid">{books.entries.map((book) => <BookCard key={book.id} book={book} />)}</div>
        : <div className="empty-state"><Icon name="books" size={32} /><h3><SiteText>এখনও কোনো বই প্রকাশিত হয়নি</SiteText></h3><p><SiteText>প্রকাশিত বই এখানে পাওয়া যাবে।</SiteText></p><Link className="text-link" href="/help/"><SiteText>পড়ার নিয়ম দেখুন</SiteText><Icon name="arrow" /></Link></div>}
    </section>
    <section className="reading-banner"><div><p className="eyebrow"><SiteText>{"আপনার পাঠের সঙ্গী"}</SiteText></p><h2><SiteText>{"নিজের পাঠাগার, নিজের মতো।"}</SiteText></h2>
      <p><SiteText>{"পড়ার অবস্থান, বুকমার্ক ও নোট এক জায়গায় রাখুন।"}</SiteText></p></div><Link className="button" href="/my-books/"><SiteText>{"আমার বইয়ে যান"}</SiteText></Link></section>
  </>;
}
