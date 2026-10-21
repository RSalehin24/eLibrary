"use client";

import { AdminDate, AdminText } from "@/components/admin-language";
import { NumberedPagination } from "./numbered-pagination";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readAccountMail, resendInvitation } from "@/api/account-mail";
import type { ManagedAccount, ResendInvitation } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { jobPollingInterval, jobStates } from "@/lib/job-status";
import { AccountFeedback } from "./account-feedback";

export function AccountMailHistory({ account }: { account: ManagedAccount }) {
  const [page, setPage] = useState(1), [operation, setOperation] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["private", "access", "account", account.id, "mail", page], queryFn: ({ signal }) => readAccountMail(account.id, page, signal),
    refetchInterval: (state) => jobPollingInterval(state.state.data?.entries ?? [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const form = useManagedForm((values: ResendInvitation) => resendInvitation(account.id, values), async () => { await query.refetch(); });
  const pagination = query.data?.pagination;
  return <section className="account-section"><h2><AdminText>{"আমন্ত্রণের ইমেইলগুলো"}</AdminText></h2>
    {account.email_setup_pending && account.is_active && !form.saving.isSuccess && <><p><AdminText>{"নতুন আমন্ত্রণের অনুরোধ করলে আগের লিংকটি বন্ধ হয়ে যাবে।"}</AdminText></p><button className="button button-quiet" disabled={form.blocked} onClick={() => {
      const identifier = operation ?? crypto.randomUUID(); setOperation(identifier); form.saving.mutate({ operation_id: identifier, expected_updated_at: account.updated_at });
    }}><AdminText>{"নতুন আমন্ত্রণের লিংক পাঠান"}</AdminText></button></>}
    {form.saving.isSuccess && <p role="status"><AdminText>{"নতুন আমন্ত্রণের অনুরোধ সংরক্ষিত হয়েছে। "}</AdminText><Link className="text-link" href={`/manage/users-access/mail/${form.saving.data.operation_id}/`}><AdminText>{"আমন্ত্রণের অবস্থা দেখুন →"}</AdminText></Link></p>}
    <AccountFeedback error={form.saving.error} />{form.saving.error && operation && <Link className="text-link" href={`/manage/users-access/mail/${operation}/`}><AdminText>{"এই অনুরোধের অবস্থা দেখুন →"}</AdminText></Link>}
    {query.isPending && <p role="status"><AdminText>{"ইমেইলের অবস্থা খোলা হচ্ছে…"}</AdminText></p>}{query.isError && <p className="field-error" role="alert"><AdminText>{"ইমেইলের অবস্থা পাওয়া যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void query.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>}
    <ul className="job-list">{query.data?.entries.map((job) => <li className="job-card" key={job.id}><Link className="text-link" href={`/manage/users-access/mail/${job.id}/`}><AdminText>{jobStates[job.state]}</AdminText> · <AdminDate value={job.created_at} /></Link></li>)}</ul>
    {pagination?.total_count === 0 && <p className="muted"><AdminText>{"কোনো আমন্ত্রণের অনুরোধ নেই।"}</AdminText></p>}
    {pagination && <NumberedPagination page={page} totalPages={Math.max(1, Math.ceil(pagination.total_count / pagination.limit))} onPageChange={setPage} busy={query.isFetching} label="আমন্ত্রণের ইমেইলের পাতা" />}</section>;
}
