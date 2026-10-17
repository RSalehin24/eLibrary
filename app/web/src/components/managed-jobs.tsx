"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readJobs } from "@/api/jobs";
import type { BackgroundJobCollection } from "@/api/types";
import { jobPollingInterval, jobStates } from "@/lib/job-status";
import { useAdminLanguage } from "./admin-language";
import { JobSummary } from "./job-summary";
import { AdminPagination } from "./admin-pagination";

export function ManagedJobs({ initial, filter }: { initial: BackgroundJobCollection; filter: string }) {
  const { t, number } = useAdminLanguage();
  const query = new URLSearchParams(filter);
  const jobs = useQuery({ queryKey: ["private", "jobs", "list", filter], queryFn: ({ signal }) => readJobs(filter, signal), initialData: initial,
    refetchInterval: (state) => jobPollingInterval(state.state.data?.entries ?? [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const data = jobs.data;
  return <><nav className="job-state-nav" aria-label={t("কাজের অবস্থা")}>{["", "queued", "running", "paused", "failed", "needs_attention", "succeeded"].map((state) => {
    const parameters = new URLSearchParams(filter); parameters.delete("page");
    if (state) parameters.set("state", state); else parameters.delete("state");
    return <Link key={state} href={`?${parameters}`} aria-current={(query.get("state") ?? "") === state ? "page" : undefined}>{t(state ? jobStates[state as keyof typeof jobStates] : "সব কাজ")}</Link>;
  })}</nav><form className="job-filters" method="get"><label htmlFor="job-state">{t("কাজের অবস্থা")}</label>
    <select id="job-state" name="state" defaultValue={query.get("state") ?? ""}><option value="">{t("সব কাজ")}</option>{Object.entries(jobStates).map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select>
    {["automation_run", "parent_job"].map((key) => query.get(key) && <input key={key} type="hidden" name={key} value={query.get(key) ?? ""} />)}<button className="button button-quiet">{t("তালিকা দেখুন")}</button></form>
    {jobs.isError && <p className="notice" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void jobs.refetch()}>{t("আবার দেখুন")}</button></p>}
    <p className="muted">{t("মোট")}: {number(data.pagination.total_count)}</p>
    <ul className="job-list">{data.entries.map((job) => <li className="job-card" key={job.id}><JobSummary job={job} /><Link className="text-link" href={`/manage/jobs/${job.id}/`}>{t("বিস্তারিত ও করণীয় →")}</Link></li>)}</ul>
    {!data.entries.length && <p className="empty-state">{t("এই অবস্থায় কোনো কাজ নেই।")}</p>}
    <AdminPagination pagination={data.pagination} filter={filter} label="কাজের তালিকার পাতা" /></>;
}
