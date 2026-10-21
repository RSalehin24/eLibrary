"use client";

import { useQuery } from "@tanstack/react-query";
import { readerAccess } from "@/api/reading";
import { ReaderLaunch } from "./reader-launch";
import { SiteText } from "./site-language";

export function ContinueReadingAction({ slug }: { slug: string }) {
  const access = useQuery({ queryKey: ["private", "reader-access", slug], queryFn: ({ signal }) => readerAccess(slug, signal), refetchOnWindowFocus: "always" });
  if (access.data && !access.data.active_session_id && (!access.data.can_read || !access.data.prepared)) return <p className="muted"><SiteText>{access.data.can_read ? "বইটি এখনো পড়ার জন্য প্রস্তুত নয়। পরে আবার দেখুন।" : "এই বই পড়ার অনুমতি এখন নেই। সহায়তার জন্য পরিচালকের সঙ্গে যোগাযোগ করুন।"}</SiteText></p>;
  if (access.data) return <ReaderLaunch slug={slug} access={access.data} />;
  if (access.isError) return <button className="button button-quiet" onClick={() => void access.refetch()}><SiteText>আবার চেষ্টা করুন</SiteText></button>;
  return <p className="muted" role="status"><SiteText>অনুমতি দেখা হচ্ছে…</SiteText></p>;
}
