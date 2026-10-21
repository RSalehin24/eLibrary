"use client";

import { useQuery } from "@tanstack/react-query";
import { readSources } from "@/api/sources";
import type { SourceEntries } from "@/api/types";
import { sourceStatuses } from "@/lib/source-status";
import { useAdminLanguage } from "./admin-language";
import { AdminPagination } from "./admin-pagination";
import { SourceSelection } from "./source-selection";

export function ManagedSources({ initial, filter }: { initial: SourceEntries; filter: string }) {
  const { t, number } = useAdminLanguage();
  const parameters = new URLSearchParams(filter);
  const emptyMessage = parameters.get("status") === "updated" ? "এই তালিকায় নতুন আপডেট নেই।" : parameters.get("catalog_scope") === "unfinished" ? "এই তালিকায় অসম্পূর্ণ বই নেই।" : "উপরে সব বইয়ের তথ্য আনুন বাটনে চাপুন। তালিকা এলে বই বেছে নিতে পারবেন।";
  const sources = useQuery({ queryKey: ["private", "sources", "list", filter], queryFn: ({ signal }) => readSources(filter, signal), initialData: initial, refetchInterval: 15000, refetchIntervalInBackground: false });
  return <section className="source-catalog"><form className="job-filters access-filters source-filters" method="get" role="search"><div className="form-field"><label htmlFor="source-query">{t("বই বা লেখকের নাম")}</label><input id="source-query" name="q" defaultValue={parameters.get("q") ?? ""} placeholder={t("বই বা লেখকের নাম")} maxLength={200} /></div>
    {parameters.get("catalog_scope") && <input type="hidden" name="catalog_scope" value={parameters.get("catalog_scope") ?? "all"} />}
    <div className="form-field"><label htmlFor="source-status">{t("উৎসের অবস্থা")}</label><select id="source-status" name="status" defaultValue={parameters.get("status") ?? "all"}>{Object.entries(sourceStatuses).map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select></div><button className="button">{t("উৎস খুঁজুন")}</button>
    <button type="button" className="button button-quiet" disabled={sources.isFetching} onClick={() => void sources.refetch()}>{t("নতুন তথ্য দেখুন")}</button><output className="source-result-count muted">{t("মোট")}: {number(sources.data.pagination.total_count)}</output></form>
    {sources.isError && <p className="field-error" role="alert">{t("হালনাগাদ তালিকা পাওয়া যায়নি।")}</p>}
    <SourceSelection entries={sources.data.entries} />
    {!sources.data.entries.length && <p className="empty-state">{t(!parameters.get("q") ? emptyMessage : "এই নামে বা অবস্থায় কোনো উৎস পাওয়া যায়নি।")}</p>}
    <AdminPagination pagination={sources.data.pagination} filter={filter} label="উৎসের তালিকার পাতা" /></section>;
}
