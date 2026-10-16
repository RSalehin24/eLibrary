"use client";

import Link from "next/link";
import type { BackgroundJob } from "@/api/types";
import { jobKinds, jobStage, jobStates, jobTimestamp } from "@/lib/job-status";
import { jobErrorMessage } from "@/lib/job-errors";
import { useAdminLanguage } from "./admin-language";

export function JobSummary({ job }: { job: BackgroundJob }) {
  const { t, language } = useAdminLanguage();
  return <><div className="job-heading"><h2><Link className="text-link" href={`/manage/jobs/${job.id}/`}>{job.book?.title ?? job.source_record?.title ?? t(jobKinds[job.kind])}</Link></h2><span className="status-label">{t(jobStates[job.state])}</span></div>
    <p>{t(jobKinds[job.kind])} · {t(jobStage(job.stage))}</p>
    {job.requested_action && <p className="notice">{t(job.requested_action === "pause" ? "স্থগিত করার অনুরোধ পাঠানো হয়েছে।" : "বাতিলের অনুরোধ পাঠানো হয়েছে।")}</p>}
    <p className="muted">{t("শুরু করার অনুরোধ")}: <time dateTime={job.created_at}>{jobTimestamp(job.created_at, language)}</time></p>
    {job.error_code && <><p className="field-error">{t(jobErrorMessage(job.error_code))}</p><details><summary>{t("সমস্যার কোড")}</summary><code>{job.error_code}</code></details></>}</>;
}
