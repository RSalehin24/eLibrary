"use client";

import Link from "next/link";
import type { WorkSummary } from "@/api/types";
import { jobKinds, jobStates, jobTimestamp } from "@/lib/job-status";
import { jobErrorMessage, waitDuration } from "@/lib/job-errors";
import { useAdminLanguage } from "./admin-language";

export function OverviewWorkGroup({ title, summary, href }: { title: string; summary: WorkSummary; href: string }) {
  const counts = summary.counts;
  const { t, number, language } = useAdminLanguage();
  const duration = counts.oldest_wait_seconds === null ? null : waitDuration(counts.oldest_wait_seconds);
  return <section className="account-section"><h2>{t(title)}</h2><dl className="book-facts">
    {(["queued", "running", "retry_wait", "paused", "failed", "needs_attention"] as const).map((state) => <div key={state}><dt>{t(jobStates[state])}</dt><dd>{href === "/manage/jobs/" ? <Link href={`${href}?state=${state}`}>{number(counts[state])}</Link> : number(counts[state])}</dd></div>)}
    <div><dt>{t("দীর্ঘতম অপেক্ষা")}</dt><dd>{duration ? `${number(duration.value)} ${t(duration.label)}` : t("শুরু করার মতো অপেক্ষমাণ কাজ নেই")}</dd></div></dl>
    <h3>{t("সাম্প্রতিক সমস্যাগুলো")}</h3><ul className="job-list">{summary.issues.map((issue) => <li className="job-card" key={issue.id}>
      <Link className="text-link" href={issue.kind === "account_mail" ? `/manage/users-access/mail/${issue.id}/` : `/manage/jobs/${issue.id}/`}>{issue.title}</Link>
      <p>{t(jobKinds[issue.kind])} · {t(jobStates[issue.state])}</p><p className="muted">{jobTimestamp(issue.finished_at, language)}</p>{issue.error_code && <p className="field-error">{t(jobErrorMessage(issue.error_code))}</p>}</li>)}</ul>
    {!summary.issues.length && <p className="muted">{t("কোনো ব্যর্থ বা অনিশ্চিত কাজ নেই।")}</p>}
    <Link className="text-link" href={href}>{t("পরিচালনার তালিকা খুলুন →")}</Link></section>;
}
