"use client";

import Link from "next/link";
import type { ReaderAccess } from "@/api/types";
import { SiteText } from "./site-language";
import { Icon } from "./icon";
import { SaveBookButton } from "./save-book-button";
import { ReaderLaunch } from "./reader-launch";

export function BookReadingActions({ slug, access }: { slug: string; access: ReaderAccess }) {
  return <>
    <ReaderLaunch slug={slug} access={access} />
    {access.html_url && <a className="button button-quiet" href={access.html_url} target="_blank" rel="noopener noreferrer"><Icon name="external" /><SiteText>HTML খুলুন</SiteText><span className="visually-hidden"> (<SiteText>নতুন ট্যাব</SiteText>)</span></a>}
    {access.can_send_kindle && <Link className="button button-quiet" href={`/kindle/books/${encodeURIComponent(slug)}/`}><Icon name="send" /><SiteText>কিন্ডলে পাঠান</SiteText></Link>}
    <SaveBookButton slug={slug} />
    {access.can_read && !access.prepared && <p className="notice"><SiteText>বইটি এখনো পড়ার জন্য প্রস্তুত নয়। পরে আবার দেখুন।</SiteText></p>}
    {!access.can_read && !access.active_session_id && <p className="notice"><SiteText>এই বই পড়ার অনুমতি এখন নেই। সহায়তার জন্য পরিচালকের সঙ্গে যোগাযোগ করুন।</SiteText></p>}
  </>;
}
