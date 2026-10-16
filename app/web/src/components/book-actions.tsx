"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { launchReader, readerAccess } from "@/api/reading";
import { APIError } from "@/api/http";
import { useUpdateParticipant } from "@/lib/update-safety";

export function BookActions({ slug, recordType }: { slug: string; recordType?: string }) {
  const router = useRouter();
  const client = useQueryClient();
  const account = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const access = useQuery({ queryKey: ["private", "reader-access", slug, account.data?.user?.id],
    queryFn: ({ signal }) => readerAccess(slug, signal), enabled: account.data?.authenticated === true && !account.data.user?.totp_setup_required });
  const launch = useMutation({ mutationFn: () => launchReader(slug), retry: false, onSuccess: (session) => {
    client.invalidateQueries({ queryKey: ["private", "reader-access", slug] }); router.push(`/reader/${session.id}/`);
  } });
  useUpdateParticipant({ dirty: launch.isPending });
  if (account.isPending) return <p className="muted" role="status">অ্যাকাউন্টের তথ্য দেখা হচ্ছে…</p>;
  if (!account.data?.authenticated) return <p className="notice">বই পড়ার অনুমতি দেখতে <Link className="text-link" href={`/login/?next=${encodeURIComponent(`/books/${slug}/`)}`}>প্রবেশ করুন</Link>।</p>;
  if (account.data.user?.totp_setup_required) return <p className="notice">বই পড়ার আগে <Link className="text-link" href={`/profile/?next=${encodeURIComponent(`/books/${slug}/`)}`}>দুই ধাপের নিরাপত্তা চালু করুন</Link>।</p>;
  if (recordType === "manual") return <p className="notice">কাগজের বইয়ের জন্য <Link className="text-link" href={`/my-books/${encodeURIComponent(slug)}/`}>পড়ার হিসাব রাখুন →</Link></p>;
  return <div className="book-actions">
    {access.data?.active_session_id ? <Link className="button" href={`/reader/${access.data.active_session_id}/`}>পড়া চালিয়ে যান</Link>
      : access.data?.can_read && access.data.prepared && <button className="button" onClick={() => launch.mutate()} disabled={launch.isPending}>{launch.isPending ? "বই খোলা হচ্ছে…" : "বই পড়ুন"}</button>}
    {access.data?.can_download && <a className="button button-quiet" href={`/api/v1/reading/books/${encodeURIComponent(slug)}/download/`}>EPUB ডাউনলোড</a>}
    {access.data?.can_send_kindle && <Link className="button button-quiet" href={`/kindle/books/${encodeURIComponent(slug)}/`}>কিন্ডলে পাঠান</Link>}
    {access.data?.can_read && !access.data.prepared && <p className="notice">বইটি এখনো পড়ার জন্য প্রস্তুত নয়। পরে আবার দেখুন।</p>}
    {access.data && !access.data.can_read && !access.data.active_session_id && <p className="notice">এই বই পড়ার অনুমতি এখন নেই। সহায়তার জন্য পরিচালকের সঙ্গে যোগাযোগ করুন।</p>}
    {access.isPending && <p className="muted" role="status">অনুমতি দেখা হচ্ছে…</p>}
    {(access.error || launch.error) && <p className="notice" role="alert">{launch.error instanceof APIError && launch.error.code === "reader_not_ready" ? "বইটি এখনো প্রস্তুত নয়। পরে আবার চেষ্টা করুন।" : "বই খোলা যায়নি। অনুমতি ও সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।"}</p>}
  </div>;
}
