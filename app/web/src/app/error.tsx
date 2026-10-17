"use client";

import { SiteText } from "@/components/site-language";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <section className="empty-state" role="alert"><h1><SiteText>{"এই মুহূর্তে তথ্য পাওয়া যাচ্ছে না"}</SiteText></h1>
    <p><SiteText>{"সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।"}</SiteText></p><button className="button" onClick={reset}><SiteText>{"আবার চেষ্টা করুন"}</SiteText></button></section>;
}
