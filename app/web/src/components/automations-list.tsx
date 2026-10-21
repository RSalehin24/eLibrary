"use client";

import { AdminNumber, AdminText } from "@/components/admin-language";
import { useQuery } from "@tanstack/react-query";
import { readAutomations } from "@/api/automations";
import type { Automations } from "@/api/types";
import { activityPollingInterval } from "@/lib/job-status";
import { AdminPagination } from "./admin-pagination";
import { AutomationListRow } from "./automation-list-row";
import Link from "next/link";
import { Icon } from "./icon";

export function AutomationsList({ initial, filter }: { initial: Automations; filter: string }) {
  const schedules = useQuery({ queryKey: ["private", "automations", "list", filter], queryFn: ({ signal }) => readAutomations(filter, signal), initialData: initial,
    refetchInterval: (query) => activityPollingInterval(false, query.state.fetchFailureCount), refetchIntervalInBackground: false });
  return <>{schedules.isError && <p className="notice" role="alert"><AdminText>{"সময়সূচি হালনাগাদ করা যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void schedules.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    <section className="admin-list-results" aria-labelledby="automation-results-heading"><header className="admin-results-heading"><h2 id="automation-results-heading"><AdminText>{"সময়সূচির তালিকা"}</AdminText><span className="count-badge"><AdminNumber value={schedules.data.pagination.total_count} /></span></h2><p><AdminText>{"পরের নির্ধারিত সময় না বদলে এখনই চালাতে পারবেন।"}</AdminText></p></header>
    {schedules.data.entries.length ? <div className="admin-data-list"><table className="admin-data-table automation-directory" role="table"><thead><tr><th scope="col"><AdminText>{"সময়সূচি"}</AdminText></th><th scope="col"><AdminText>{"কী কাজ চলবে"}</AdminText></th><th scope="col"><AdminText>{"পরের নির্ধারিত সময়"}</AdminText></th><th scope="col"><AdminText>{"করণীয়"}</AdminText></th></tr></thead>
      <tbody>{schedules.data.entries.map(schedule => <AutomationListRow key={schedule.id} schedule={schedule} />)}</tbody></table></div>
      : <div className="admin-list-empty"><Icon name="schedule" size={32} /><h2><AdminText>{"কোনো সময়সূচি পাওয়া যায়নি।"}</AdminText></h2><p><AdminText>{"নতুন সময়সূচি তৈরি করুন অথবা ফিল্টার বদলে দেখুন।"}</AdminText></p><Link className="button" href="/manage/automations/new/"><Icon name="plus" /><AdminText>{"নতুন সময়সূচি"}</AdminText></Link></div>}
    </section><AdminPagination pagination={schedules.data.pagination} filter={filter} label="সময়সূচির পাতা" /></>;
}
