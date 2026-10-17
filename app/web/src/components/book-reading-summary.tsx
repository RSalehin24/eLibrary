"use client";

import { useQuery } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { readerAccess } from "@/api/reading";
import { PersonalNotes } from "./personal-notes";
import { SiteDate, SiteNumber, SiteText } from "./site-language";

export function BookReadingSummary({ slug }: { slug: string }) {
  const account = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const authenticated = account.data?.authenticated === true && !account.data.user?.totp_setup_required;
  const access = useQuery({ queryKey: ["private", "reader-access", slug], queryFn: ({ signal }) => readerAccess(slug, signal), enabled: authenticated, refetchOnWindowFocus: "always" });
  if (!authenticated) return null;
  const reading = access.data?.reading_progress;
  return <section className="book-reading-summary">
    <h2><SiteText>আপনার পড়া ও নোট</SiteText></h2>
    {reading && <dl className="book-facts"><div><dt><SiteText>পড়ার অগ্রগতি</SiteText></dt><dd><SiteNumber value={Math.round(reading.progress_percent)} />%</dd></div><div><dt><SiteText>শেষবার পড়েছেন</SiteText></dt><dd><SiteDate value={access.data?.last_opened_at ?? null} /></dd></div></dl>}
    <PersonalNotes book={slug} />
  </section>;
}
