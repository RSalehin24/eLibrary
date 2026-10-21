"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { launchReader } from "@/api/reading";
import type { ReaderAccess } from "@/api/types";
import { APIError } from "@/api/http";
import { useUpdateParticipant } from "@/lib/update-safety";
import { SiteText } from "./site-language";
import { Icon } from "./icon";

export function ReaderLaunch({ slug, access }: { slug: string; access: ReaderAccess }) {
  const router = useRouter(), client = useQueryClient();
  const launch = useMutation({ mutationFn: () => launchReader(slug), retry: false, onSuccess: session => {
    void client.invalidateQueries({ queryKey: ["private", "reader-access", slug] });
    router.push(`/reader/${session.id}/`);
  } });
  useUpdateParticipant({ dirty: launch.isPending });
  return <>{access.active_session_id ? <Link className="button" href={`/reader/${access.active_session_id}/`}><Icon name="read" /><SiteText>পড়া চালিয়ে যান</SiteText></Link>
    : access.can_read && access.prepared && <button type="button" className="button" onClick={() => launch.mutate()} disabled={launch.isPending}><Icon name="read" /><SiteText>{launch.isPending ? "বই খোলা হচ্ছে…" : "বই পড়ুন"}</SiteText></button>}
    {launch.error && <p className="notice" role="alert"><SiteText>{launch.error instanceof APIError && launch.error.code === "reader_not_ready" ? "বইটি এখনো প্রস্তুত নয়। পরে আবার চেষ্টা করুন।" : "বই খোলা যায়নি। অনুমতি ও সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।"}</SiteText></p>}
  </>;
}
