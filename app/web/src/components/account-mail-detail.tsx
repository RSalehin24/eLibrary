"use client";

import { AdminDate, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { controlMailOperation, readMailOperation } from "@/api/account-mail";
import type { AccountMailOperation, JobControl } from "@/api/types";
import { isJobAction, jobActions, jobPollingInterval, jobStates } from "@/lib/job-status";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AccountFeedback } from "./account-feedback";

export function AccountMailDetail({ initial }: { initial: AccountMailOperation }) {
  const client = useQueryClient(), key = ["private", "access", "mail", initial.id];
  const query = useQuery({ queryKey: key, initialData: initial, queryFn: ({ signal }) => readMailOperation(initial.id, signal), refetchInterval: (state) => jobPollingInterval(state.state.data ? [state.state.data] : [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const job = query.data;
  const command = useMutation({ mutationFn: (action: JobControl["action"]) => controlMailOperation(job.id, { action, expected_updated_at: job.updated_at }), retry: false, gcTime: 0,
    onSuccess: async () => { await client.invalidateQueries({ queryKey: key }); } });
  useUpdateParticipant({ dirty: command.isPending });
  async function refresh() { const result = await query.refetch(); if (result.isSuccess) command.reset(); }
  return <section className="account-settings"><h1><AdminText>{"আমন্ত্রণের ইমেইল"}</AdminText></h1><span className="status-label"><AdminText>{jobStates[job.state]}</AdminText></span>
    <p><Link className="text-link" href={`/manage/users-access/${job.account_id}/`}><AdminText>{"পাঠকের হিসাব ও অনুমতি দেখুন →"}</AdminText></Link></p>
    <dl className="book-facts"><div><dt><AdminText>{"অনুরোধের পরিচয়"}</AdminText></dt><dd className="job-identifier">{job.id}</dd></div><div><dt><AdminText>{"অনুরোধের সময়"}</AdminText></dt><dd><AdminDate value={job.created_at} /></dd></div><div><dt><AdminText>{"ইমেইল সেবায় গৃহীত"}</AdminText></dt><dd><AdminDate value={job.accepted_at} /></dd></div></dl>
    <p className="muted"><AdminText>{"ইমেইল সেবায় গৃহীত হওয়ার পরও পাঠকের ইনবক্সে পৌঁছাতে সময় লাগতে পারে।"}</AdminText></p>
    {job.requested_action && <p className="notice"><AdminText>{"থামানোর অনুরোধ পাঠানো হয়েছে। ইমেইল জমা দেওয়ার আগে কাজটি থামবে। ইতিমধ্যে জমা হয়ে থাকলে ফল সংরক্ষিত হবে।"}</AdminText></p>}
    {job.error_code && <p className="field-error"><AdminText>{"সমস্যার পরিচয়: "}</AdminText><code>{job.error_code}</code></p>}
    {job.state === "needs_attention" && <p className="notice"><AdminText>{"ইমেইল গৃহীত হয়েছিল কি না নিশ্চিত নয়। স্বয়ংক্রিয়ভাবে আবার পাঠানো হবে না। নতুন আমন্ত্রণ চাইলে পাঠকের হিসাব থেকে পাঠান; পুরোনো লিংক বন্ধ হয়ে যাবে।"}</AdminText></p>}
    {query.isError && <p role="alert" className="field-error"><AdminText>{"বর্তমান অবস্থা পাওয়া যায়নি।"}</AdminText></p>}<AccountFeedback error={command.error} />
    <div className="account-actions">{job.actions.filter(isJobAction).map((action) => <button key={action} className="button button-quiet" disabled={command.isPending || !!command.error || query.isError} onClick={() => command.mutate(action)}>{jobActions[action]}</button>)}
      <button className="button button-quiet" onClick={() => void refresh()} disabled={command.isPending || query.isFetching}><AdminText>{"বর্তমান অবস্থা দেখুন"}</AdminText></button></div></section>;
}
