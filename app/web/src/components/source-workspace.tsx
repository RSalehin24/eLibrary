"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readSource } from "@/api/sources";
import type { SourceEntry } from "@/api/types";
import { AdminDate, useAdminLanguage } from "./admin-language";
import { ProcessingAssets } from "./processing-assets";
import { SourceProcessing } from "./source-processing";
import { SourceSummary } from "./source-summary";
import { SourceVerification } from "./source-verification";

export function SourceWorkspace({ initial }: { initial: SourceEntry }) {
  const { t, number } = useAdminLanguage();
  const source = useQuery({ queryKey: ["private", "sources", "detail", initial.id], queryFn: ({ signal }) => readSource(initial.id, signal), initialData: initial, refetchInterval: 5000, refetchIntervalInBackground: false });
  const entry = source.data, book = entry.book && !entry.book.deleted_at ? entry.book : null;
  const operation = entry.active_operation_id ?? entry.latest_operation_id;
  return <div className="source-workspace"><Link className="text-link" href="/manage/sources/">{t("← উৎসের তালিকায় ফিরুন")}</Link>
    <SourceSummary entry={entry} />
    <div className="source-result-actions">{book && entry.can_edit_book && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/`}>{t("সম্পাদনা, পর্যালোচনা ও প্রকাশ")}</Link>}
      {book && operation && <Link className="button button-quiet" href={`/manage/jobs/${operation}/`}>{t(entry.active_operation_id ? "চলমান কাজ ও করণীয় দেখুন →" : "কাজের বিস্তারিত")}</Link>}</div>
    {source.isError && <p className="field-error" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void source.refetch()}>{t("আবার দেখুন")}</button></p>}
    {entry.content_summary && <section className="source-content-summary"><p className="muted">{t("পাওয়া অধ্যায়")}: {number(entry.content_summary.chapter_count)} · {t("লেখার অক্ষর")}: {number(entry.content_summary.body_character_count)}</p>
      <SourceVerification verification={entry.content_summary.verification} />
      {entry.content_summary.check_completeness && !entry.content_summary.verification?.verified && <p className="notice" role="status">{t("স্বয়ংক্রিয় যাচাই সম্পূর্ণ হয়নি। বইটি আবার প্রসেস করুন।")}</p>}</section>}
    {book ? <ProcessingAssets slug={book.slug} /> : <SourceProcessing entry={entry} />}
    <section className="source-provenance"><h2>{t("ওয়েবসাইটের তথ্য")}</h2><p className="muted">{t("উৎসে শেষ দেখা:")} <AdminDate value={entry.last_seen_at} /></p>
      {entry.source_url ? <a className="text-link" href={entry.source_url} target="_blank" rel="noopener noreferrer">{t("মূল উৎস খুলুন (নতুন ট্যাব) ↗")}</a> : <p className="notice">{t("মূল উৎসের ব্যবহারযোগ্য ঠিকানা পাওয়া যায়নি।")}</p>}</section>
  </div>;
}
