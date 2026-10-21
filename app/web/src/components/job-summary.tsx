"use client";

import Link from "next/link";
import type { BackgroundJob } from "@/api/types";
import { jobKinds, jobStage, jobStates, jobTimestamp } from "@/lib/job-status";
import { jobErrorMessage } from "@/lib/job-errors";
import { useAdminLanguage } from "./admin-language";

export function JobSummary({ job }: { job: BackgroundJob }) {
  const { t, language } = useAdminLanguage();
  const emptyDiscovery = job.kind === "discover_source" && job.state === "succeeded" && job.discovered_entries === 0;
  const waitingForSource = job.state === "retry_wait" && job.error_code === "source_content_unavailable";
  return <><div className="job-heading"><h2><Link className="text-link" href={`/manage/jobs/${job.id}/`}>{job.book?.title ?? job.source_record?.title ?? t(jobKinds[job.kind])}</Link></h2><span className={`status-label status-${job.state}`}>{t(emptyDiscovery ? "কোনো বই পাওয়া যায়নি" : jobStates[job.state])}</span></div>
    <p>{t(jobKinds[job.kind])} · {t(emptyDiscovery ? "আবার সংগ্রহ করুন" : waitingForSource ? "ওয়েবসাইটে লেখা আসার অপেক্ষা" : jobStage(job.stage))}</p>
    {job.requested_action && <p className="notice">{t(job.requested_action === "pause" ? "স্থগিত করার অনুরোধ পাঠানো হয়েছে।" : "বাতিলের অনুরোধ পাঠানো হয়েছে।")}</p>}
    <p className="muted">{t("শুরু করার অনুরোধ")}: <time dateTime={job.created_at}>{jobTimestamp(job.created_at, language)}</time></p>
    {job.error_code && <><p className={job.state === "retry_wait" ? "muted" : "field-error"}>{t(jobErrorMessage(job.error_code))}</p><details><summary>{t("সমস্যার কোড")}</summary><code>{job.error_code}</code></details></>}
    {job.source_defect && ["failed", "needs_attention"].includes(job.state) && <div className="notice"><p>{t("প্রসেসিং কোডের সমস্যা ধরা পড়েছে। সংশ্লিষ্ট কোড হালনাগাদ হলে বই তৈরির কাজ নিজে থেকে আবার শুরু হবে।")}</p><Link className="text-link" href={`/manage/jobs/?q=${job.source_defect.fingerprint}`}>{t("একই সমস্যার কাজগুলো দেখুন")}</Link></div>}</>;
}
