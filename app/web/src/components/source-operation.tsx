"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { controlJob, readJob } from "@/api/jobs";
import type { JobControl } from "@/api/types";
import { isJobAction, jobActionLabel, jobPollingInterval, jobStates } from "@/lib/job-status";
import { jobErrorMessage } from "@/lib/job-errors";
import { useAdminLanguage } from "./admin-language";
import { AccountFeedback } from "./account-feedback";

export function SourceOperation({ id }: { id: string }) {
  const { t, number } = useAdminLanguage();
  const client = useQueryClient(), settled = useRef("");
  const query = useQuery({ queryKey: ["private", "jobs", "detail", id], queryFn: ({ signal }) => readJob(id, signal), refetchInterval: (state) => jobPollingInterval(state.state.data ? [state.state.data] : [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const job = query.data;
  const control = useMutation({ mutationFn: (action: JobControl["action"]) => { if (!job) throw new Error("Job unavailable"); return controlJob(job, action); }, onSuccess: async () => { await client.invalidateQueries({ queryKey: ["private", "jobs"] }); } });
  useEffect(() => {
    if (job && ["succeeded", "failed", "cancelled"].includes(job.state) && settled.current !== job.id) {
      settled.current = job.id;
      void client.invalidateQueries({ queryKey: ["private", "sources"] });
      void client.invalidateQueries({ queryKey: ["private", "catalog-processing"] });
      void client.invalidateQueries({ queryKey: ["private", "discovery-options"] });
    }
  }, [job, client]);
  if (!job) return <p className={query.isError ? "field-error" : "muted"}>{t(query.isError ? "অবস্থা দেখা যাচ্ছে না। আবার চেষ্টা করুন।" : "তথ্য লোড হচ্ছে…")}</p>;
  const bulk = job.kind === "process_catalog";
  const empty = job.kind === "discover_source" && job.state === "succeeded" && !job.discovered_entries;
  return <div className="source-operation"><span className={`status-label status-${empty ? "failed" : job.state}`}>{t(empty ? "কোনো বই পাওয়া যায়নি" : jobStates[job.state])}</span>
    <p className="operation-count">{bulk ? `${t("তালিকায় যোগ হয়েছে")}: ${number(job.bulk_queued)} / ${number(job.bulk_total)}` : `${number(job.discovered_pages)} ${t("পাতা")} · ${number(job.discovered_entries)} ${t("বই")}`}</p>
    {bulk && job.bulk_rejected > 0 && <p className="field-error">{t("যোগ করা যায়নি")}: {number(job.bulk_rejected)}</p>}
    {job.error_code && <p className="field-error">{t(jobErrorMessage(job.error_code))}</p>}
    {empty && <p className="field-error">{t(jobErrorMessage("source_catalog_empty"))}</p>}
    {job.more_pages_available && <p className="notice">{t("· নির্ধারিত পাতার সীমা পূর্ণ হয়েছে; উৎসে আরও পাতা আছে।")}</p>}
    <div className="operation-actions">{job.actions.filter(isJobAction).map((action) => <button key={action} className="button button-quiet" disabled={control.isPending || !!control.error} onClick={() => control.mutate(action)}>{t(jobActionLabel(job.kind, action))}</button>)}
      <Link className="text-link" href={`/manage/jobs/${job.id}/`}>{t("কাজের বিস্তারিত")}</Link>{bulk && job.bulk_queued > 0 && <Link className="text-link" href={`/manage/jobs/?parent_job=${job.id}`}>{t("বইয়ের কাজ দেখুন")}</Link>}</div>
    {bulk && job.actions.length > 0 && <p className="muted">{t("ইতিমধ্যে যোগ হওয়া বইয়ের কাজ চলতে থাকবে।")}</p>}
    <AccountFeedback error={control.error} />{query.isError && <p className="field-error" role="alert">{t("অবস্থা দেখা যাচ্ছে না। আবার চেষ্টা করুন।")}</p>}
  </div>;
}
