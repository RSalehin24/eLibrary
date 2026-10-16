"use client";

import { AdminNumber, AdminText } from "@/components/admin-language";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { readSourceIssue, resolveSourceIssue } from "@/api/source-processing";
import type { BackgroundJobDetail, SourceIssue, SourceResolution } from "@/api/types";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";

const decisions: Record<SourceResolution["choice"], string> = {
  retry: "মূল উৎস আবার সংগ্রহ করুন", link: "আগের বইয়ের সঙ্গে এই উৎস সংযুক্ত করুন",
  separate: "আলাদা বই হিসেবে খসড়া তৈরি করুন", resume_preparation: "আগের খসড়ার প্রস্তুতি চালিয়ে যান", cancel: "এই কাজ বাতিল করুন",
};

function availableDecisions(issue: SourceIssue): SourceResolution["choice"][] {
  return Object.keys(decisions).filter((choice): choice is SourceResolution["choice"] => issue.available_choices.includes(choice));
}

export function SourceIssueForm({ job }: { job: BackgroundJobDetail }) {
  const query = useQuery({ queryKey: ["private", "jobs", "detail", job.id, "source-issue"], queryFn: ({ signal }) => readSourceIssue(job.id, signal), staleTime: Infinity, refetchOnWindowFocus: false, refetchOnReconnect: false });
  if (query.isPending) return <p role="status"><AdminText>{"উৎসের যাচাই খোলা হচ্ছে…"}</AdminText></p>;
  if (query.isError) return <p className="field-error" role="alert"><AdminText>{"উৎসের যাচাই পাওয়া যায়নি। "}</AdminText><button className="button button-quiet" onClick={() => void query.refetch()}><AdminText>{"আবার দেখুন"}</AdminText></button></p>;
  if (!availableDecisions(query.data).length) return <p className="notice"><AdminText>{"এই কাজ এখন সিদ্ধান্তের অপেক্ষায় নেই। বর্তমান অবস্থা দেখুন।"}</AdminText></p>;
  return <SourceDecision key={query.data.expected_updated_at} job={job} issue={query.data} />;
}

function SourceDecision({ job, issue }: { job: BackgroundJobDetail; issue: SourceIssue }) {
  const choices = availableDecisions(issue), client = useQueryClient();
  const [choice, setChoice] = useState<SourceResolution["choice"]>(choices[0]);
  const form = useManagedForm((values: SourceResolution) => resolveSourceIssue(job.id, values), async () => { await client.invalidateQueries({ queryKey: ["private", "jobs"] }); });
  return <form className="account-section" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget), book = String(fields.get("book_id") || ""), candidate = issue.candidates.find((entry) => entry.id === book);
    form.saving.mutate({ expected_updated_at: issue.expected_updated_at, choice, ...(choice === "link" && candidate ? { book_id: book, expected_book_updated_at: candidate.updated_at } : {}) });
  }}><h2><AdminText>{job.error_code === "source_duplicate" ? "একই নামে বই পাওয়া গেছে" : "উৎসের কাজের করণীয়"}</AdminText></h2>
    <p>{issue.title} {issue.author_line && `· ${issue.author_line}`}</p><p className="muted"><AdminText>{"যাচাইয়ের সমস্যা: "}</AdminText><AdminNumber value={issue.error_count} /><AdminText>{" · সতর্কতা: "}</AdminText><AdminNumber value={issue.warning_count} /></p>
    <div className="form-field"><label htmlFor="source-resolution"><AdminText>{"করণীয় নির্বাচন করুন"}</AdminText></label><select id="source-resolution" value={choice} disabled={form.blocked} onChange={(event) => setChoice(event.target.value as SourceResolution["choice"])}>
      {choices.map((decision) => <option value={decision} key={decision}>{decisions[decision]}</option>)}</select></div>
    {choice === "link" && <div className="form-field"><label htmlFor="source-candidate"><AdminText>{"সংযুক্ত করার বই"}</AdminText></label><select id="source-candidate" name="book_id" required disabled={form.blocked} defaultValue=""><option value=""><AdminText>{"বই নির্বাচন করুন"}</AdminText></option>{issue.candidates.map((book) => <option key={book.id} value={book.id}>{book.title} · {book.catalog_code}</option>)}</select></div>}
    {choice === "separate" && <p className="notice"><AdminText>{"আগের বই অক্ষত থাকবে। এই উৎসের আলাদা খসড়া সম্পাদকের যাচাইয়ে যাবে।"}</AdminText></p>}
    {choice === "retry" && <p className="muted"><AdminText>{"আগের সংগ্রহের বদলে উৎসের বর্তমান লেখা আবার আনা হবে।"}</AdminText></p>}
    {choice === "resume_preparation" && <p className="muted"><AdminText>{"সংরক্ষিত লেখা থেকে আগের খসড়ার প্রস্তুতি আবার চলবে। সম্পন্ন অংশগুলো পুনর্ব্যবহার করা হবে।"}</AdminText></p>}
    <AccountFeedback error={form.saving.error} /><button className="button" disabled={form.blocked}><AdminText>{"সিদ্ধান্ত সংরক্ষণ করুন"}</AdminText></button>
    {form.saving.error && <><p className="muted"><AdminText>{"আবার পাঠানোর আগে কাজের বর্তমান অবস্থা খুলুন। আপনার নির্বাচন স্বয়ংক্রিয়ভাবে আবার জমা হবে না।"}</AdminText></p><button className="button button-quiet" type="button" onClick={reloadManagedForm}><AdminText>{"বর্তমান যাচাই খুলুন"}</AdminText></button></>}</form>;
}
