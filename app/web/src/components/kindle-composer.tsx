"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { kindleOptions } from "@/api/kindle";
import type { KindleOptions } from "@/api/types";
import { useKindleForm } from "@/lib/kindle-form";
import { bengaliNumber } from "@/lib/site";
import { AccountFeedback } from "./account-feedback";
import { APIError } from "@/api/http";

function KindleRequestForm({ options }: { options: KindleOptions }) {
  const { sending, submit, markDirty } = useKindleForm(options);
  const invalidSelection = sending.error instanceof APIError && sending.error.status === 400;
  const blocked = sending.isPending || (!!sending.error && !invalidSelection) || !!sending.data;
  return <form className="account-section" onChange={markDirty} onSubmit={(event) => {
    event.preventDefault(); submit(new FormData(event.currentTarget).getAll("recipient").map(String));
  }}><h2>যে ঠিকানাগুলোতে পাঠাবেন</h2><p>প্রতি অনুরোধে সর্বোচ্চ ১০টি ঠিকানা এবং {bengaliNumber(options.max_attachment_bytes / (1024 * 1024))} MiB ফাইল পাঠানো যায়।</p>
    <fieldset disabled={blocked} aria-invalid={invalidSelection} aria-describedby={invalidSelection ? "kindle-recipient-errors" : undefined}><legend>প্রোফাইলের কিন্ডল ঠিকানা</legend>
      {options.recipients.map((address) => <label className="checkbox-field" key={address}><input type="checkbox" name="recipient" value={address} defaultChecked /><span className="kindle-address" lang="en">{address}</span></label>)}</fieldset>
    <AccountFeedback error={sending.error} conflictMessage="বই বা পাঠানোর তথ্য বদলেছে। বর্তমান অবস্থা দেখে আবার সিদ্ধান্ত নিন।" />
    {invalidSelection && <p id="kindle-recipient-errors" className="field-error">অন্তত একটি প্রোফাইলের ঠিকানা বেছে নিন। সর্বোচ্চ ১০টি ঠিকানা পাঠানো যাবে।</p>}
    {sending.error && sending.variables && <p>আবার পাঠানোর আগে <Link className="text-link" href={`/kindle/operations/${sending.variables.operation_id}/`}>এই অনুরোধের ফল দেখুন</Link>।</p>}
    {sending.data ? <p role="status">অনুরোধ গ্রহণ করা হয়েছে। <Link className="text-link" href={`/kindle/operations/${sending.data.operation_id}/`}>পাঠানোর অবস্থা দেখুন →</Link></p> : <button className="button" disabled={!options.configured || !options.recipients.length || blocked}>{sending.isPending ? "অনুরোধ পাঠানো হচ্ছে…" : "বই পাঠানোর অনুরোধ করুন"}</button>}
    <p><button className="button button-quiet" type="button" disabled={sending.isPending} onClick={() => window.location.reload()}>বর্তমান তথ্য খুলুন</button> নতুন তথ্য খুললে সংরক্ষণ না করা নির্বাচন আবার করতে হতে পারে।</p>
  </form>;
}

export function KindleComposer({ initial }: { initial: KindleOptions }) {
  const options = useQuery({ queryKey: ["private", "kindle", "options", initial.book.slug], queryFn: ({ signal }) => kindleOptions(initial.book.slug, signal), initialData: initial, refetchOnWindowFocus: false });
  const data = options.data;
  return <div className="account-settings"><p>মেইল সার্ভার গ্রহণ করলে এখানকার অবস্থা বদলাবে। কিন্ডলে পৌঁছেছে কি না আপনার যন্ত্রে দেখে নিশ্চিত করুন।</p>
    {data.sender_email && <p>Amazon-এর অনুমোদিত প্রেরকের তালিকায় <strong lang="en">{data.sender_email}</strong> যোগ করুন।</p>}
    {!data.configured && <p className="notice">কিন্ডলে পাঠানোর সেবা এখন প্রস্তুত নয়। পরিচালকের সঙ্গে যোগাযোগ করুন।</p>}
    {!data.recipients.length && <p className="notice">আগে <Link className="text-link" href="/profile/">প্রোফাইলে কিন্ডলের ঠিকানা যোগ করুন</Link>।</p>}
    {options.isError && <p className="field-error" role="alert">বর্তমান তথ্য পাওয়া যায়নি।</p>}
    <KindleRequestForm key={data.asset_revision + data.recipients.join(",")} options={data} /></div>;
}
