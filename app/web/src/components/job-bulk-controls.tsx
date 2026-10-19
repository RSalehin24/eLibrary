"use client";

import { useRef } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { controlJobSelection } from "@/api/jobs";
import type { BackgroundJob } from "@/api/types";
import { jobActions } from "@/lib/job-status";
import { availableBulkActions, bulkActionEntries, sourceBulkActions, sourceBulkActionLabels, type JobBulkAction } from "@/lib/job-bulk-actions";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AdminNumber, AdminText, useAdminLanguage } from "./admin-language";
import { AccountFeedback } from "./account-feedback";
import { Icon } from "./icon";

export function JobBulkControls({ selected, onAccepted, onClear, disabled, available, sourceAvailable }: { selected: BackgroundJob[]; onAccepted: (identifiers: string[]) => void; onClear: () => void; disabled: boolean; available: boolean; sourceAvailable: boolean }) {
  const { t } = useAdminLanguage(), client = useQueryClient();
  const command = useRef({ signature: "", identifier: "" });
  const mutation = useMutation({ mutationFn: controlJobSelection, retry: false, onSuccess: async (result) => {
    onAccepted(result.entries.filter((entry) => entry.outcome === "accepted").map((entry) => entry.id));
    await client.invalidateQueries({ queryKey: ["private", "jobs"] });
  } });
  useUpdateParticipant({ dirty: mutation.isPending });
  function act(action: JobBulkAction) {
    const entries = bulkActionEntries(selected, action);
    const signature = JSON.stringify([action, entries]);
    if (command.current.signature !== signature) command.current = { signature, identifier: crypto.randomUUID() };
    mutation.mutate({ operation_id: command.current.identifier, action, entries });
  }
  if (!available && !selected.length && !mutation.isSuccess && !mutation.isError) return null;
  return <section className="account-section" aria-label={t("নির্বাচিত কাজ পরিচালনা")}>
    <div className="account-actions"><strong><AdminText>{"নির্বাচিত"}</AdminText>: <AdminNumber value={selected.length} /></strong>{(["pause", "resume", "cancel"] as const).map((action) => <button className="button button-quiet" type="button" key={action} disabled={disabled || mutation.isPending || !selected.length || selected.some((job) => !availableBulkActions(job).includes(action))} onClick={() => act(action)}><Icon name={action === "resume" ? "refresh" : action === "cancel" ? "trash" : "schedule"} /><AdminText>{jobActions[action]}</AdminText></button>)}{selected.length > 0 && <button type="button" className="button button-quiet" disabled={mutation.isPending} onClick={onClear}><Icon name="refresh" /><AdminText>{"নির্বাচন সরান"}</AdminText></button>}</div>
    {sourceAvailable && <><div className="account-actions">{sourceBulkActions.map(action => <button className="button button-quiet" type="button" key={action} disabled={disabled || mutation.isPending || !selected.length || selected.some(job => !availableBulkActions(job).includes(action))} onClick={() => act(action)}><Icon name={action === "archive_book" ? "books" : "refresh"} /><AdminText>{sourceBulkActionLabels[action]}</AdminText></button>)}</div>
    <p className="muted"><AdminText>আবার চেষ্টা করলে সংরক্ষিত কাজ চালানো হবে। নতুন করে তৈরি করলে ওয়েবসাইট থেকে বর্তমান লেখা আনা হবে। আর্কাইভের বই পরে আবার প্রকাশ করা যাবে।</AdminText></p></>}
    <p className="muted"><AdminText>{"নির্বাচিত সব কাজে প্রযোজ্য নিয়ন্ত্রণগুলো ব্যবহার করা যাবে। কাজের ইতিহাস সংরক্ষিত থাকবে।"}</AdminText></p>
    <AccountFeedback error={mutation.error} conflictMessage="কাজের অবস্থাটি বদলেছে। বর্তমান অবস্থা দেখে আবার করণীয় বেছে নিন।" />
    {mutation.isSuccess && <div role="status"><p><AdminNumber value={mutation.data.entries.filter((entry) => entry.outcome === "accepted").length} /> <AdminText>{"টি কাজের অনুরোধ গ্রহণ করা হয়েছে।"}</AdminText></p>
      {mutation.data.entries.some((entry) => entry.outcome !== "accepted") && <p><AdminText>{"কিছু কাজ বদলে গেছে বা পাওয়া যায়নি। তালিকা হালনাগাদ করে সেগুলো আবার নির্বাচন করুন।"}</AdminText></p>}
      <ul>{mutation.data.entries.filter((entry) => entry.outcome !== "accepted").map((entry) => <li key={entry.id}><Link className="text-link" href={`/manage/jobs/${entry.id}/`}>{selected.find((job) => job.id === entry.id)?.book?.title ?? selected.find((job) => job.id === entry.id)?.source_record?.title ?? entry.id}</Link> · <AdminText>{entry.outcome === "conflict" ? "কাজের তথ্য বদলেছে" : entry.outcome === "forbidden" ? "এই কাজের অনুমতি নেই" : entry.outcome === "rejected" ? "এই বইয়ে কাজটি এখন করা যাবে না" : "কাজটি পাওয়া যায়নি"}</AdminText></li>)}</ul>
    </div>}
  </section>;
}
