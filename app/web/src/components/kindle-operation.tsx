"use client";

import { SiteText } from "@/components/site-language";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelKindle, kindleOperation } from "@/api/kindle";
import type { KindleOperation as Operation } from "@/api/types";
import { jobPollingInterval } from "@/lib/job-status";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AccountFeedback } from "./account-feedback";
import { KindleSummary } from "./kindle-summary";
import { KindleResendLink } from "./kindle-resend-link";

export function KindleOperation({ initial }: { initial: Operation }) {
  const client = useQueryClient();
  const status = useQuery({ queryKey: ["private", "kindle", "operation", initial.id], queryFn: ({ signal }) => kindleOperation(initial.id, signal), initialData: initial,
    refetchInterval: (query) => jobPollingInterval(query.state.data ? [query.state.data] : [], query.state.fetchFailureCount), refetchIntervalInBackground: false });
  const cancellation = useMutation({ mutationFn: () => cancelKindle(status.data), onSuccess: async () => { await client.invalidateQueries({ queryKey: ["private", "kindle"] }); } });
  useUpdateParticipant({ dirty: cancellation.isPending });
  async function refresh() { if ((await status.refetch()).isSuccess) cancellation.reset(); }
  return <section className="account-section"><KindleSummary operation={status.data} />
    {status.data.recipients.some((recipient) => recipient.outcome === "accepted") && <p className="muted"><SiteText>{"মেইল সার্ভার ইতিমধ্যে গ্রহণ করেছে এমন বই বাতিল করে ফেরানো যাবে না।"}</SiteText></p>}
    <AccountFeedback error={cancellation.error} conflictMessage="পাঠানোর অবস্থা বদলেছে। বর্তমান ফল দেখে সিদ্ধান্ত নিন।" />
    {status.isError && <p className="field-error" role="alert"><SiteText>{"হালনাগাদ অবস্থা পাওয়া যায়নি।"}</SiteText></p>}
    <div className="account-actions">{status.data.can_cancel && <button className="button button-quiet" disabled={cancellation.isPending || !!cancellation.error || status.isError} onClick={() => cancellation.mutate()}><SiteText>{"পাঠানো বাতিল করুন"}</SiteText></button>}
      <button className="button button-quiet" disabled={cancellation.isPending || status.isFetching} onClick={() => void refresh()}><SiteText>{"বর্তমান অবস্থা দেখুন"}</SiteText></button><KindleResendLink operation={status.data} /></div></section>;
}
