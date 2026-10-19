"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readJobs } from "@/api/jobs";
import type { BackgroundJob, BackgroundJobCollection } from "@/api/types";
import { jobPollingInterval } from "@/lib/job-status";
import { jobViewLabels } from "@/lib/job-filters";
import { availableBulkActions } from "@/lib/job-bulk-actions";
import { useAdminLanguage } from "./admin-language";
import { JobSummary } from "./job-summary";
import { AdminPagination } from "./admin-pagination";
import { JobFiltersForm } from "./job-filters-form";
import { JobBulkControls } from "./job-bulk-controls";
import { Icon } from "./icon";
import { SourceVerification } from "./source-verification";
import { SourceLayoutSummary } from "./source-layout-summary";

export function ManagedJobs({ initial, filter }: { initial: BackgroundJobCollection; filter: string }) {
  const { t, number } = useAdminLanguage();
  const [selected, setSelected] = useState<Record<string, BackgroundJob>>({});
  const query = new URLSearchParams(filter);
  const jobs = useQuery({ queryKey: ["private", "jobs", "list", filter], queryFn: ({ signal }) => readJobs(filter, signal), initialData: initial,
    refetchInterval: (state) => jobPollingInterval(state.state.data?.entries ?? [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const data = jobs.data;
  const eligible = data.entries.filter((job) => availableBulkActions(job).length > 0);
  return <><nav className="job-state-nav" aria-label={t("কাজের তালিকা")}>{["", ...Object.keys(jobViewLabels)].map((view) => {
    const parameters = new URLSearchParams(filter); parameters.delete("page"); parameters.delete("state");
    if (view) parameters.set("view", view); else parameters.delete("view");
    return <Link key={view} href={`?${parameters}`} aria-current={(query.get("view") ?? "") === view ? "page" : undefined}><Icon name={view === "recovery" ? "warning" : view === "history" ? "notes" : "jobs"} />{t(view ? jobViewLabels[view] : "সব কাজ")}</Link>;
  })}</nav>
    {query.get("book") && <p className="notice"><Icon name="books" />{t("এই বইয়ের কাজ")}: {data.entries.find((job) => job.book)?.book?.title ?? t("নির্বাচিত বই")}</p>}
    {query.get("parent_job") && <p className="notice">{t("একসঙ্গে যোগ করা বইগুলোর কাজ দেখানো হচ্ছে।")}</p>}
    {query.get("automation_run") && <p className="notice">{t("নির্বাচিত অটোমেশন চালনার কাজ দেখানো হচ্ছে।")}</p>}
    <JobFiltersForm filter={filter} />
    {jobs.isError && <p className="notice" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void jobs.refetch()}>{t("আবার দেখুন")}</button></p>}
    <p className="muted">{t("মোট")}: {number(data.pagination.total_count)}</p>
    {eligible.length > 0 && <label className="selection-toggle"><input type="checkbox" disabled={jobs.isFetching} checked={eligible.every((job) => !!selected[job.id])} onChange={(event) => setSelected(event.target.checked ? Object.fromEntries(eligible.map((job) => [job.id, job])) : {})} />{t("এই পাতার কাজগুলো নির্বাচন করুন")}</label>}
    <JobBulkControls selected={Object.values(selected)} available={eligible.length > 0} sourceAvailable={data.entries.some(job => job.kind === "process_source")} disabled={jobs.isError} onClear={() => setSelected({})} onAccepted={(identifiers) => setSelected((previous) => Object.fromEntries(Object.entries(previous).filter(([identifier]) => !identifiers.includes(identifier))))} />
    <ul className="job-list">{data.entries.map((job) => <li className="job-card" key={job.id}>{availableBulkActions(job).length > 0 && <label className="selection-toggle"><input type="checkbox" checked={!!selected[job.id]} onChange={(event) => setSelected((previous) => event.target.checked ? { ...previous, [job.id]: job } : Object.fromEntries(Object.entries(previous).filter(([identifier]) => identifier !== job.id)))} />{t("নির্বাচন করুন")}: <span translate="no">{job.book?.title ?? job.source_record?.title ?? job.id}</span></label>}<JobSummary job={job} />
      <SourceLayoutSummary layout={job.source_layout} />
      {job.verification && <details><summary>{t("লেখার যাচাই")}</summary><SourceVerification verification={job.verification} /><p>{t(job.exports_verified ? "HTML ও EPUB-এর লেখা মিলেছে" : "HTML ও EPUB-এর যাচাই বাকি")}</p></details>}
      <div className="account-actions"><Link className="button button-quiet" href={`/manage/jobs/${job.id}/`}><Icon name="settings" />{t("বিস্তারিত ও করণীয় →")}</Link>{job.book && <Link className="text-link" href={`/manage/jobs/?book=${job.book.id}`}><Icon name="books" />{t("এই বইয়ের সব কাজ")}</Link>}</div></li>)}</ul>
    {!data.entries.length && <p className="empty-state">{t("এই অবস্থায় কোনো কাজ নেই।")}</p>}
    <AdminPagination pagination={data.pagination} filter={filter} label="কাজের তালিকার পাতা" /></>;
}
