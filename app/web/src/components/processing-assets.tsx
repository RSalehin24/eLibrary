"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { prepareAsset, readProcessingAssets } from "@/api/jobs";
import type { ProcessingAsset } from "@/api/types";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AccountFeedback } from "./account-feedback";

function AssetPreparation({ asset }: { asset: ProcessingAsset }) {
  const command = useMutation({ mutationFn: (identifier: string) => prepareAsset(asset, identifier) });
  useUpdateParticipant({ dirty: command.isPending });
  return <div className="job-card"><p><strong>{asset.asset_type.toUpperCase()}</strong></p>
    {asset.asset_type === "epub" && asset.status === "ready" && !command.data && <button className="button button-quiet" disabled={command.isPending || !!command.error} onClick={() => command.mutate(crypto.randomUUID())}><AdminText>{command.isPending ? "অনুরোধ পাঠানো হচ্ছে…" : "পড়ার জন্য প্রস্তুত করুন"}</AdminText></button>}
    {command.data && <Link className="text-link" href={`/manage/jobs/${command.data.operation_id}/`}><AdminText>{"প্রস্তুতির কাজ দেখুন →"}</AdminText></Link>}
    <AccountFeedback error={command.error} conflictMessage="বইয়ের উপকরণ বদলেছে। বর্তমান তথ্য খুলে আবার পরীক্ষা করুন।" />{command.error && <p><AdminText>{"পুনরায় পাঠানোর আগে "}</AdminText><Link className="text-link" href={`/manage/jobs/${command.variables}/`}><AdminText>{"এই অনুরোধের ফল দেখুন"}</AdminText></Link><AdminText>{" অথবা "}</AdminText><Link className="text-link" href="/manage/jobs/"><AdminText>{"কাজের তালিকা খুলুন"}</AdminText></Link>।</p>}
    {asset.status !== "ready" && <p className="muted"><AdminText>{"উপকরণটি এখন প্রস্তুত নয়।"}</AdminText></p>}</div>;
}

export function ProcessingAssets({ slug }: { slug: string }) {
  const assets = useQuery({ queryKey: ["private", "processing-assets", slug], queryFn: ({ signal }) => readProcessingAssets(slug, signal) });
  return <section className="account-section"><h2><AdminText>{"পড়ার উপকরণ"}</AdminText></h2><p><AdminText>{"EPUB পরীক্ষা ও প্রস্তুতি আলাদা কাজ হিসেবে চলবে। ফল কাজের তালিকায় দেখতে পারবেন।"}</AdminText></p>
    {assets.isPending && <p role="status"><AdminText>{"উপকরণ পাওয়া হচ্ছে…"}</AdminText></p>}
    {assets.isError && <p className="field-error" role="alert"><AdminText>{"উপকরণ পাওয়া যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void assets.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    {assets.data?.map((asset) => <AssetPreparation key={asset.id + asset.updated_at} asset={asset} />)}
    {assets.data?.length === 0 && <p><AdminText>{"এই বইয়ের জন্য এখনও কোনো উপকরণ নেই।"}</AdminText></p>}</section>;
}
