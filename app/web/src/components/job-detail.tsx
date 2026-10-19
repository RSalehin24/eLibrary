"use client";

import { AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { BackgroundJobDetail } from "@/api/types";
import { isJobAction, jobActionLabel } from "@/lib/job-status";
import { useJobDetail } from "@/lib/job-detail";
import { AccountFeedback } from "./account-feedback";
import { JobSummary } from "./job-summary";
import { JobAttempts, JobFacts } from "./job-facts";
import { SourceIssueForm } from "./source-issue-form";
import { JobProgress } from "./job-progress";
import { Icon } from "./icon";
import { SourceVerification } from "./source-verification";
import { SourceLayoutSummary } from "./source-layout-summary";

export function JobDetail({ initial }: { initial: BackgroundJobDetail }) {
  const { job, query, command, refresh } = useJobDetail(initial);
  return <section className="job-detail"><JobSummary job={job} />
    <JobProgress job={job} />
    <SourceLayoutSummary layout={job.source_layout} />
    {job.verification && <><SourceVerification verification={job.verification} /><p><AdminText>{job.exports_verified ? "HTML ও EPUB-এর লেখা মিলেছে" : "HTML ও EPUB-এর যাচাই বাকি"}</AdminText></p></>}
    {job.can_edit_book && job.book && <p><Link className="text-link" href={`/manage/books/${encodeURIComponent(job.book.slug)}/`}><AdminText>{"বইয়ের তথ্য দেখুন →"}</AdminText></Link></p>}
    {job.kind === "process_catalog" && <div className="notice"><p><AdminText>{"তালিকায় যোগ হয়েছে"}</AdminText>: <AdminNumber value={job.bulk_queued} /> / <AdminNumber value={job.bulk_total} /> · <AdminText>{"যোগ করা যায়নি"}</AdminText>: <AdminNumber value={job.bulk_rejected} /></p><Link className="button button-quiet" href={`/manage/jobs/?parent_job=${job.id}`}><AdminText>{"বইয়ের কাজ দেখুন"}</AdminText></Link><p><AdminText>{"ইতিমধ্যে যোগ হওয়া বইয়ের কাজ চলতে থাকবে।"}</AdminText></p></div>}
    {job.source_record && <p><Link className="text-link" href={`/manage/sources/${job.source_record.id}/`}><AdminText>{"উৎসের তথ্য দেখুন →"}</AdminText></Link><AdminText>{" · সংগৃহীত পাতা: "}</AdminText><AdminNumber value={job.pages_fetched} /></p>}
    {job.kind === "discover_source" && <DiscoveryResult job={job} />}
    {job.kind === "process_source" && ["needs_attention", "failed"].includes(job.state) && <SourceIssueForm job={job} />}
    {job.state === "needs_attention" && job.kind !== "process_source" && <p className="notice"><AdminText>{"আগের কাজের ফল নিশ্চিত করা প্রয়োজন। আবার পাঠানোর আগে পরিচালকের পরীক্ষা দরকার।"}</AdminText></p>}
    <AccountFeedback error={command.error} conflictMessage="কাজের অবস্থাটি বদলেছে। বর্তমান অবস্থা দেখে আবার করণীয় বেছে নিন।" />{query.isError && <p className="field-error" role="alert"><AdminText>{"হালনাগাদ অবস্থা পাওয়া যায়নি।"}</AdminText></p>}
    <div className="account-actions job-controls">{job.actions.filter(isJobAction).map((action) => <button className="button button-quiet" key={action} disabled={command.isPending || !!command.error || query.isError} onClick={() => command.mutate(action)}><Icon name={action === "resume" ? "refresh" : action === "cancel" ? "trash" : "schedule"} /><AdminText>{jobActionLabel(job.kind, action)}</AdminText></button>)}
      <button className="button button-quiet" onClick={() => void refresh()} disabled={command.isPending || query.isFetching}><Icon name="refresh" /><AdminText>{"বর্তমান অবস্থা দেখুন"}</AdminText></button></div>
    <details className="job-technical"><summary><Icon name="settings" /><AdminText>কারিগরি তথ্য</AdminText></summary><JobFacts job={job} /></details>
    {job.attempts.length > 0 && <details className="job-technical"><summary><Icon name="jobs" /><AdminText>আগের চেষ্টাগুলো</AdminText></summary><JobAttempts job={job} /></details>}</section>;
}

function DiscoveryResult({ job }: { job: BackgroundJobDetail }) {
  const emptySuccess = job.state === "succeeded" && job.discovered_entries === 0;
  return <div className="discovery-result">
    <p><AdminText>{"সংগৃহীত পাতা: "}</AdminText><AdminNumber value={job.discovered_pages} /><AdminText>{" · পাওয়া পরিচিতি: "}</AdminText><AdminNumber value={job.discovered_entries} />{job.more_pages_available && <AdminText>{" · নির্ধারিত পাতার সীমা পূর্ণ হয়েছে; উৎসে আরও পাতা আছে।"}</AdminText>}</p>
    {emptySuccess && <p className="notice" role="alert"><AdminText>{"এই কাজে কোনো বই সংগ্রহ হয়নি। বই তৈরির তালিকায় ফিরে আবার সংগ্রহ করুন।"}</AdminText></p>}
    {["succeeded", "failed", "cancelled"].includes(job.state) && <p><Link className="text-link" href="/manage/sources/"><AdminText>{job.discovered_entries > 0 ? "বই বেছে নিয়ে তৈরি করুন →" : "তালিকায় ফিরে আবার সংগ্রহ করুন →"}</AdminText></Link></p>}
  </div>;
}
