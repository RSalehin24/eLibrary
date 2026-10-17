"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { prepareAsset, readProcessingAssets } from "@/api/jobs";
import type { ProcessingAsset } from "@/api/types";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AdminText, useAdminLanguage } from "./admin-language";
import { AccountFeedback } from "./account-feedback";
import { readerAccess } from "@/api/reading";
import { BookReadingActions } from "./book-reading-actions";

function AssetFile({ asset }: { asset: ProcessingAsset }) {
  const { t, number } = useAdminLanguage();
  const client = useQueryClient();
  const command = useMutation({ mutationFn: (identifier: string) => prepareAsset(asset, identifier), onSuccess: () => client.invalidateQueries({ queryKey: ["private", "processing-assets"] }) });
  useUpdateParticipant({ dirty: command.isPending });
  const operation = asset.active_preparation_id ?? command.data?.operation_id;
  return <article className="asset-file"><div className="asset-file-format" aria-hidden="true">{asset.asset_type.toUpperCase()}</div><div className="asset-file-info"><h3>{asset.asset_type.toUpperCase()}</h3>
    <p className={asset.file_available ? "muted" : "field-error"}>{t(asset.file_available ? "ফাইল তৈরি হয়েছে" : asset.status === "ready" ? "ফাইলটি পাওয়া যাচ্ছে না" : "ফাইল এখনও তৈরি হয়নি")}{asset.file_available && ` · ${number(asset.file_size)} ${t("বাইট")}`}</p>
    {asset.asset_type === "epub" && asset.file_available && <p className="muted">{t(asset.reader_ready ? "অনলাইনে পড়ার জন্য প্রস্তুত" : operation ? "অনলাইনে পড়ার প্রস্তুতি চলছে" : "অনলাইনে পড়ার প্রস্তুতি বাকি")}</p>}
    </div><div className="asset-file-actions">{asset.download_url && <a className="button button-quiet" href={asset.download_url} download>{t("ডাউনলোড")} {asset.asset_type.toUpperCase()}</a>}
    {asset.file_available && !asset.download_url && <p className="muted">{t("ফাইল নামানোর অনুমতি নেই।")}</p>}
    {asset.asset_type === "epub" && asset.file_available && (!asset.reader_ready || asset.reader_update_available) && !operation && <button className="button button-quiet" disabled={command.isPending || !!command.error} onClick={() => command.mutate(crypto.randomUUID())}>{t(command.isPending ? "অনুরোধ পাঠানো হচ্ছে…" : asset.reader_ready ? "পড়ার ফাইল হালনাগাদ করুন" : "পড়ার জন্য প্রস্তুত করুন")}</button>}
    {operation && (!asset.reader_ready || asset.reader_update_available) && <Link className="text-link" href={`/manage/jobs/${operation}/`}>{t("প্রস্তুতির কাজ দেখুন →")}</Link>}
    </div><AccountFeedback error={command.error} conflictMessage="বইয়ের উপকরণ বদলেছে। বর্তমান তথ্য খুলে আবার পরীক্ষা করুন।" />
    {command.error && <Link className="text-link" href={`/manage/jobs/${command.variables}/`}>{t("এই অনুরোধের ফল দেখুন")}</Link>}
  </article>;
}

export function ProcessingAssets({ slug }: { slug: string }) {
  const access = useQuery({ queryKey: ["private", "reader-access", slug], queryFn: ({ signal }) => readerAccess(slug, signal), refetchInterval: 5000, refetchIntervalInBackground: false });
  const assets = useQuery({ queryKey: ["private", "processing-assets", slug], queryFn: ({ signal }) => readProcessingAssets(slug, signal), refetchInterval: 5000, refetchIntervalInBackground: false });
  const readingFiles = assets.data?.filter(asset => asset.asset_type === "epub" || asset.asset_type === "html");
  return <section className="book-files account-section" id="book-files"><div className="book-reading-actions">{access.data && <BookReadingActions slug={slug} access={access.data} />}
    {access.isPending && <p className="muted" role="status"><AdminText>অনুমতি দেখা হচ্ছে…</AdminText></p>}
    {access.isError && <p className="notice" role="alert"><AdminText>পড়ার অনুমতি দেখা যায়নি।</AdminText> <button className="button button-quiet" onClick={() => void access.refetch()}><AdminText>আবার দেখুন</AdminText></button></p>}</div>
    <div className="section-heading"><h2><AdminText>বইয়ের ফাইল</AdminText></h2><button className="button button-quiet" disabled={assets.isFetching || access.isFetching} onClick={() => { void assets.refetch(); void access.refetch(); }}><AdminText>নতুন তথ্য দেখুন</AdminText></button></div>
    {assets.isPending && <p role="status"><AdminText>ফাইলের তথ্য আসছে…</AdminText></p>}
    {assets.isError && <p className="field-error" role="alert"><AdminText>উপকরণ পাওয়া যায়নি। </AdminText><button className="button button-quiet" onClick={() => void assets.refetch()}><AdminText>আবার দেখুন</AdminText></button></p>}
    <div className="asset-files">{readingFiles?.map((asset) => <AssetFile key={asset.id + asset.updated_at} asset={asset} />)}</div>
    <p className="muted"><AdminText>ফাইল খুলে বইয়ের সম্পূর্ণ লেখা আছে কি না যাচাই করুন। তারপর পর্যালোচনা করে প্রকাশ করুন।</AdminText></p>
    {readingFiles?.length === 0 && <p className="notice"><AdminText>এই বইয়ের জন্য এখনও কোনো উপকরণ নেই।</AdminText></p>}
  </section>;
}
