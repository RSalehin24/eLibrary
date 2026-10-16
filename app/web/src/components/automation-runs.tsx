"use client";

import { AdminDate, AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readAutomationRuns } from "@/api/automations";
import type { AutomationRuns, BackgroundJob } from "@/api/types";
import { automationErrors } from "@/lib/automation-status";
import { activityPollingInterval, jobStates } from "@/lib/job-status";
import { AdminPagination } from "./admin-pagination";

export function AutomationRunHistory({ id, initial, filter }: { id: string; initial: AutomationRuns; filter: string }) {
  const runs = useQuery({ queryKey: ["private", "automations", id, "runs", filter], queryFn: ({ signal }) => readAutomationRuns(id, filter, signal), initialData: initial,
    refetchInterval: (query) => activityPollingInterval(query.state.data?.entries.some((run) => run.processing_active > 0 || ["queued", "running", "retry_wait"].includes(run.job_state ?? "")) ?? false, query.state.fetchFailureCount), refetchIntervalInBackground: false });
  return <section className="account-section"><h2><AdminText>{"চলার ইতিহাস"}</AdminText></h2>{runs.isError && <p role="alert" className="notice"><AdminText>{"হালনাগাদ ইতিহাস পাওয়া যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void runs.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    <ul className="job-list">{runs.data.entries.map((run) => <li className="job-card" key={run.id}><h3><AdminDate value={run.due_at} /></h3>
      {run.state === "blocked" ? <p className="notice">{automationErrors[run.error_code] ?? "এইবারের কাজ শুরু করা যায়নি। কনফিগারেশন ও অনুমতি পরীক্ষা করুন।"}</p> : <><p><AdminText>{"উৎস আবিষ্কার: "}</AdminText>{jobStates[run.job_state as BackgroundJob["state"]] ?? "অবস্থা পাওয়া যায়নি"}</p><Link className="text-link" href={`/manage/jobs/${run.job_id}/`}><AdminText>{"উৎস আবিষ্কারের বিস্তারিত ও নিয়ন্ত্রণ →"}</AdminText></Link></>}
      <p><AdminText>{"প্রস্তুতির কাজ "}</AdminText><AdminNumber value={run.processing_count} /><AdminText>{"টি · সম্পন্ন "}</AdminText><AdminNumber value={run.processing_succeeded} /><AdminText>{"টি · চলমান "}</AdminText><AdminNumber value={run.processing_active} /><AdminText>{"টি · পরীক্ষা প্রয়োজন "}</AdminText><AdminNumber value={run.processing_attention} /><AdminText>{"টি"}</AdminText></p>
      {run.processing_rejected > 0 && <p className="notice"><AdminNumber value={run.processing_rejected} /><AdminText>{"টি উৎসের প্রস্তুতি শুরু হয়নি। "}</AdminText><Link className="text-link" href="/manage/sources/"><AdminText>{"উৎসের বর্তমান তথ্য পরীক্ষা করুন →"}</AdminText></Link></p>}
      {run.processing_count > 0 && <Link className="text-link" href={`/manage/jobs/?automation_run=${run.id}`}><AdminText>{"এইবারের বই প্রস্তুতির কাজ দেখুন →"}</AdminText></Link>}
      {run.missed_occurrences > 0 && <p className="muted"><AdminText>{"বিরতির সময়ে বাদ পড়া "}</AdminText><AdminNumber value={run.missed_occurrences} /><AdminText>{"টি সময়ের জন্য অতিরিক্ত কাজ তৈরি হয়নি।"}</AdminText></p>}</li>)}</ul>
    {!runs.data.entries.length && <p className="empty-state"><AdminText>{"এখনও এই সময়সূচি থেকে কোনো কাজ শুরু হয়নি।"}</AdminText></p>}<AdminPagination pagination={runs.data.pagination} filter={filter} label="চলার ইতিহাসের পাতা" /></section>;
}
