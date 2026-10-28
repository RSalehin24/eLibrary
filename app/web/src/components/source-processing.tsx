"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { processSource } from "@/api/source-processing";
import type { SourceEntry, SourceProcessingCommand } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";

export function SourceProcessing({ entry }: { entry: SourceEntry }) {
  const client = useQueryClient();
  const [identifier, setIdentifier] = useState<string | null>(null);
  const form = useManagedForm((values: SourceProcessingCommand) => processSource(entry.id, values), async () => { await client.invalidateQueries({ queryKey: ["private", "sources"] }); });
  return <section className="account-section"><h2><AdminText>{"উৎস থেকে বই প্রস্তুত"}</AdminText></h2><p><AdminText>{"উৎসের লেখা ও পড়ার ফাইল প্রস্তুত হবে। স্বয়ংক্রিয় যাচাই সফল হলে বই প্রকাশিত হবে।"}</AdminText></p>
    {entry.active_operation_id && <Link className="text-link" href={`/manage/jobs/${entry.active_operation_id}/`}><AdminText>{"চলমান কাজ ও করণীয় দেখুন →"}</AdminText></Link>}
    {!entry.active_operation_id && entry.latest_operation_id && <p><Link className="text-link" href={`/manage/jobs/${entry.latest_operation_id}/`}><AdminText>{"সর্বশেষ কাজ ও করণীয় দেখুন →"}</AdminText></Link></p>}
    {!entry.active_operation_id && !form.saving.isSuccess && entry.can_process && <button className="button" disabled={form.blocked} onClick={() => {
      const operationId = identifier ?? crypto.randomUUID(); setIdentifier(operationId);
      form.saving.mutate({ operation_id: operationId, expected_updated_at: entry.updated_at });
    }}><AdminText>{"এই উৎস প্রক্রিয়ার অনুরোধ করুন"}</AdminText></button>}
    {!entry.active_operation_id && !entry.can_process && <p className="notice"><AdminText>{entry.book ? "এই উৎস বইয়ের সঙ্গে সংযুক্ত। আগের কাজের করণীয় ও প্রস্তুত সম্পদ দেখুন।" : "প্রক্রিয়ার জন্য ব্যবহারযোগ্য উৎস ও পরিচালকের কনফিগারেশন পরীক্ষা করুন।"}</AdminText></p>}
    {form.saving.isSuccess && <p role="status"><AdminText>{"কাজের অনুরোধ সংরক্ষিত হয়েছে। "}</AdminText><Link className="text-link" href={`/manage/jobs/${form.saving.data.operation_id}/`}><AdminText>{"কাজের অবস্থা দেখুন →"}</AdminText></Link></p>}
    <AccountFeedback error={form.saving.error} />{form.saving.error && identifier && <p><Link className="text-link" href={`/manage/jobs/${identifier}/`}><AdminText>{"এই অনুরোধের ফল দেখুন →"}</AdminText></Link></p>}</section>;
}
