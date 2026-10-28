"use client";

import { SiteText } from "@/components/site-language";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { readerAccess } from "@/api/reading";
import { BookReadingActions } from "./book-reading-actions";

export function BookActions({ slug }: { slug: string }) {
  const account = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const access = useQuery({ queryKey: ["private", "reader-access", slug],
    queryFn: ({ signal }) => readerAccess(slug, signal), refetchOnWindowFocus: "always", enabled: account.data?.authenticated === true && !account.data.user?.totp_setup_required });
  if (account.isPending) return <p className="muted" role="status"><SiteText>{"অ্যাকাউন্টের তথ্য দেখা হচ্ছে…"}</SiteText></p>;
  if (!account.data?.authenticated) return <p className="notice"><SiteText>{"বই পড়ার অনুমতি দেখতে "}</SiteText><Link className="text-link" href={`/login/?next=${encodeURIComponent(`/books/${slug}/`)}`}><SiteText>{"প্রবেশ করুন"}</SiteText></Link>।</p>;
  if (account.data.user?.totp_setup_required) return <p className="notice"><SiteText>{"বই পড়ার আগে "}</SiteText><Link className="text-link" href={`/profile/?next=${encodeURIComponent(`/books/${slug}/`)}`}><SiteText>{"দুই ধাপের নিরাপত্তা চালু করুন"}</SiteText></Link>।</p>;
  return <div className="book-actions">
    {!access.isError && access.data?.can_edit_book && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(slug)}/`}><SiteText>বইয়ের তথ্য সম্পাদনা করুন</SiteText></Link>}
    {access.data && <BookReadingActions slug={slug} access={access.data} />}
    {access.data?.can_download && <a className="button button-quiet" href={`/api/v1/reading/books/${encodeURIComponent(slug)}/download/`}><SiteText>{"EPUB ডাউনলোড"}</SiteText></a>}
    {access.isPending && <p className="muted" role="status"><SiteText>{"অনুমতি দেখা হচ্ছে…"}</SiteText></p>}
    {access.error && <p className="notice" role="alert"><SiteText>বই খোলা যায়নি। অনুমতি ও সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।</SiteText><button type="button" className="button button-quiet" onClick={() => void access.refetch()}><SiteText>আবার চেষ্টা করুন</SiteText></button></p>}
  </div>;
}
