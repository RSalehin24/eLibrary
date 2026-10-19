"use client";

import { useQuery } from "@tanstack/react-query";
import { bookDetailPreview } from "@/api/reading";
import { bookDetailContents, type ContentsBranch } from "@/lib/book-detail-contents";
import { SiteText } from "./site-language";
import "./book-detail-preview.css";

function ContentsList({ entries }: { entries: ContentsBranch[] }) {
  return <>{entries.map((entry, index) => <li key={index}>{entry.label}{entry.children.length > 0 && <ol><ContentsList entries={entry.children} /></ol>}</li>)}</>;
}

export function BookDetailPreview({ slug }: { slug: string }) {
  const preview = useQuery({ queryKey: ["private", "book-detail-preview", slug], queryFn: ({ signal }) => bookDetailPreview(slug, signal), refetchOnWindowFocus: "always" });
  if (preview.isPending) return <p role="status"><SiteText>বইয়ের সূচি দেখা হচ্ছে…</SiteText></p>;
  if (preview.error) return <p className="notice" role="alert"><SiteText>বইয়ের সূচি ও প্রকাশনার তথ্য দেখা যায়নি।</SiteText> <button className="button button-quiet" onClick={() => void preview.refetch()}><SiteText>আবার চেষ্টা করুন</SiteText></button></p>;
  const details = preview.data;
  if (!details.front_matter.length && !details.front_matter_text && !details.dedication && !details.contents.length && !details.truncated) return null;
  return <section className="book-detail-preview">
    {(details.front_matter.length > 0 || details.front_matter_text) && <section><h2><SiteText>প্রকাশনার তথ্য</SiteText></h2>{details.front_matter.length > 0 ? <dl className="book-facts">{details.front_matter.map((entry, index) => <div key={index}><dt><SiteText>{entry.label}</SiteText></dt><dd>{entry.value}</dd></div>)}</dl> : <p className="book-description">{details.front_matter_text}</p>}</section>}
    {details.dedication && <section><h2><SiteText>উৎসর্গ</SiteText></h2><p className="book-description">{details.dedication}</p></section>}
    {details.contents.length > 0 && <section><h2><SiteText>সূচিপত্র</SiteText></h2><ol className="book-detail-contents"><ContentsList entries={bookDetailContents(details.contents)} /></ol></section>}
    {details.truncated && <p className="notice"><SiteText>এখানে সংক্ষিপ্ত তথ্য দেখানো হয়েছে। পুরো সূচি ও লেখা দেখতে বই পড়ুন।</SiteText></p>}
  </section>;
}
