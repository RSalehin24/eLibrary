"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { launchAnnotation, type AnnotationKind } from "@/api/annotations";
import { APIError } from "@/api/http";
import { useUpdateParticipant } from "@/lib/update-safety";
import { Icon } from "./icon";
import { SiteText } from "./site-language";

export function AnnotationReaderAction({ kind, identifier, disabled = false }: { kind: AnnotationKind; identifier: string; disabled?: boolean }) {
  const router = useRouter();
  const launch = useMutation({ mutationFn: () => launchAnnotation(kind, identifier), retry: false,
    onSuccess: (session) => router.push(`/reader/${session.id}/?${new URLSearchParams({ [kind === "bookmarks" ? "bookmark" : "highlight"]: identifier })}`) });
  useUpdateParticipant({ dirty: launch.isPending });
  return <div className="annotation-actions"><button type="button" className="button button-quiet" disabled={disabled || launch.isPending} onClick={() => launch.mutate()}><Icon name="read" /><SiteText>{launch.isPending ? "বই খোলা হচ্ছে…" : "রিডারে খুলুন"}</SiteText></button>
    {launch.error && <p className="notice" role="alert"><SiteText>{launch.error instanceof APIError && launch.error.code === "reader_not_ready" ? "নোটের বইয়ের এই সংস্করণটি এখন পাওয়া যাচ্ছে না। আপনার নোট সংরক্ষিত আছে।" : "বই খোলা যায়নি। অনুমতি ও সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।"}</SiteText></p>}
  </div>;
}
