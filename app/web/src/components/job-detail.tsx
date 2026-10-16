"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import type { BackgroundJobDetail } from "@/api/types";
import { isJobAction, jobActions } from "@/lib/job-status";
import { useJobDetail } from "@/lib/job-detail";
import { AccountFeedback } from "./account-feedback";
import { JobSummary } from "./job-summary";
import { JobAttempts, JobFacts } from "./job-facts";
import { SourceIssueForm } from "./source-issue-form";

export function JobDetail({ initial }: { initial: BackgroundJobDetail }) {
  const { job, query, command, refresh } = useJobDetail(initial);
  return <section className="job-detail"><JobSummary job={job} />
    {job.can_edit_book && job.book && <p><Link className="text-link" href={`/manage/books/${encodeURIComponent(job.book.slug)}/`}><AdminText>{"বইয়ের তথ্য দেখুন →"}</AdminText></Link></p>}
    <JobFacts job={job} />
    {job.source_record && <p><Link className="text-link" href={`/manage/sources/${job.source_record.id}/`}><AdminText>{"উৎসের তথ্য দেখুন →"}</AdminText></Link><AdminText>{" · সংগৃহীত পাতা: "}</AdminText>{job.pages_fetched}</p>}
    {job.kind === "discover_source" && <p><AdminText>{"সংগৃহীত পাতা: "}</AdminText>{job.discovered_pages}<AdminText>{" · পাওয়া পরিচিতি: "}</AdminText>{job.discovered_entries}{job.more_pages_available && " · নির্ধারিত পাতার সীমা পূর্ণ হয়েছে; উৎসে আরও পাতা আছে।"}</p>}
    {job.kind === "process_source" && ["needs_attention", "failed"].includes(job.state) && <SourceIssueForm job={job} />}
    {job.state === "needs_attention" && job.kind !== "process_source" && <p className="notice"><AdminText>{"আগের কাজের ফল নিশ্চিত করা প্রয়োজন। আবার পাঠানোর আগে পরিচালকের পরীক্ষা দরকার।"}</AdminText></p>}
    <AccountFeedback error={command.error} conflictMessage="কাজের অবস্থাটি বদলেছে। বর্তমান অবস্থা দেখে আবার করণীয় বেছে নিন।" />{query.isError && <p className="field-error" role="alert"><AdminText>{"হালনাগাদ অবস্থা পাওয়া যায়নি।"}</AdminText></p>}
    <div className="account-actions">{job.actions.filter(isJobAction).map((action) => <button className="button button-quiet" key={action} disabled={command.isPending || !!command.error || query.isError} onClick={() => command.mutate(action)}>{jobActions[action]}</button>)}
      <button className="button button-quiet" onClick={() => void refresh()} disabled={command.isPending || query.isFetching}><AdminText>{"বর্তমান অবস্থা দেখুন"}</AdminText></button></div>
    <JobAttempts job={job} /></section>;
}
