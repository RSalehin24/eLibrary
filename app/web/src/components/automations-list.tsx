"use client";

import { AdminDate, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readAutomations } from "@/api/automations";
import type { Automations } from "@/api/types";
import { automationFrequencies } from "@/lib/automation-status";
import { activityPollingInterval } from "@/lib/job-status";
import { AdminPagination } from "./admin-pagination";

export function AutomationsList({ initial, filter }: { initial: Automations; filter: string }) {
  const schedules = useQuery({ queryKey: ["private", "automations", "list", filter], queryFn: ({ signal }) => readAutomations(filter, signal), initialData: initial,
    refetchInterval: (query) => activityPollingInterval(false, query.state.fetchFailureCount), refetchIntervalInBackground: false });
  return <>{schedules.isError && <p className="notice" role="alert"><AdminText>{"সময়সূচি হালনাগাদ করা যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void schedules.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    <ul className="job-list">{schedules.data.entries.map((schedule) => <li key={schedule.id} className="job-card"><h2><Link href={`/manage/automations/${schedule.id}/`}>{schedule.name}</Link></h2>
      <p><AdminText>{schedule.enabled ? "সক্রিয়" : "বন্ধ"}</AdminText> · <AdminText>{automationFrequencies[schedule.frequency]}</AdminText></p><p><AdminText>{"পরের নির্ধারিত সময়: "}</AdminText><AdminDate value={schedule.next_run_at} /></p><p className="muted"><AdminText>{"অনুমতি: "}</AdminText>{schedule.run_as_name}<AdminText>{" · স্থানীয় সময়ের অঞ্চল: "}</AdminText>{schedule.time_zone}</p>
      <Link className="text-link" href={`/manage/automations/${schedule.id}/`}><AdminText>{"সময়সূচি ও চলার ইতিহাস →"}</AdminText></Link></li>)}</ul>
    {!schedules.data.entries.length && <p className="empty-state"><AdminText>{"কোনো স্বয়ংক্রিয় সময়সূচি তৈরি হয়নি।"}</AdminText></p>}<AdminPagination pagination={schedules.data.pagination} filter={filter} label="সময়সূচির পাতা" /></>;
}
