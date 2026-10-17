"use client";

import { SiteText, SiteNumber } from "@/components/site-language";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { kindleOptions } from "@/api/kindle";
import type { KindleOptions } from "@/api/types";
import { useKindleForm } from "@/lib/kindle-form";
import { AccountFeedback } from "./account-feedback";
import { APIError } from "@/api/http";

function KindleRequestForm({ options }: { options: KindleOptions }) {
  const { sending, submit, markDirty } = useKindleForm(options);
  const invalidSelection = sending.error instanceof APIError && sending.error.status === 400;
  const blocked = sending.isPending || (!!sending.error && !invalidSelection) || !!sending.data;
  return <form className="account-section" onChange={markDirty} onSubmit={(event) => {
    event.preventDefault(); submit(new FormData(event.currentTarget).getAll("recipient").map(String));
  }}><h2><SiteText>{"যে ঠিকানাগুলোতে পাঠাবেন"}</SiteText></h2><p><SiteText>{"প্রতি অনুরোধে সর্বোচ্চ ১০টি ঠিকানা এবং "}</SiteText><SiteNumber value={options.max_attachment_bytes / (1024 * 1024)} /><SiteText>{" MiB ফাইল পাঠানো যায়।"}</SiteText></p>
    <fieldset disabled={blocked} aria-invalid={invalidSelection} aria-describedby={invalidSelection ? "kindle-recipient-errors" : undefined}><legend><SiteText>{"প্রোফাইলের কিন্ডল ঠিকানা"}</SiteText></legend>
      {options.recipients.map((address) => <label className="checkbox-field" key={address}><input type="checkbox" name="recipient" value={address} defaultChecked /><span className="kindle-address" lang="en">{address}</span></label>)}</fieldset>
    <AccountFeedback error={sending.error} conflictMessage="বই বা পাঠানোর তথ্য বদলেছে। বর্তমান অবস্থা দেখে আবার সিদ্ধান্ত নিন।" />
    {invalidSelection && <p id="kindle-recipient-errors" className="field-error"><SiteText>{"অন্তত একটি প্রোফাইলের ঠিকানা বেছে নিন। সর্বোচ্চ ১০টি ঠিকানা পাঠানো যাবে।"}</SiteText></p>}
    {sending.error && sending.variables && <p><SiteText>{"আবার পাঠানোর আগে "}</SiteText><Link className="text-link" href={`/kindle/operations/${sending.variables.operation_id}/`}><SiteText>{"এই অনুরোধের ফল দেখুন"}</SiteText></Link>।</p>}
    {sending.data ? <p role="status"><SiteText>{"অনুরোধ গ্রহণ করা হয়েছে। "}</SiteText><Link className="text-link" href={`/kindle/operations/${sending.data.operation_id}/`}><SiteText>{"পাঠানোর অবস্থা দেখুন →"}</SiteText></Link></p> : <button className="button" disabled={!options.configured || !options.recipients.length || blocked}>{sending.isPending ? <SiteText>{"অনুরোধ পাঠানো হচ্ছে…"}</SiteText> : <SiteText>{"বই পাঠানোর অনুরোধ করুন"}</SiteText>}</button>}
    <p><button className="button button-quiet" type="button" disabled={sending.isPending} onClick={() => window.location.reload()}><SiteText>{"বর্তমান তথ্য খুলুন"}</SiteText></button><SiteText>{" নতুন তথ্য খুললে সংরক্ষণ না করা নির্বাচন আবার করতে হতে পারে।"}</SiteText></p>
  </form>;
}

export function KindleComposer({ initial }: { initial: KindleOptions }) {
  const options = useQuery({ queryKey: ["private", "kindle", "options", initial.book.slug], queryFn: ({ signal }) => kindleOptions(initial.book.slug, signal), initialData: initial, refetchOnWindowFocus: false });
  const data = options.data;
  return <div className="account-settings"><p><SiteText>{"মেইল সার্ভার গ্রহণ করলে এখানকার অবস্থা বদলাবে। কিন্ডলে পৌঁছেছে কি না আপনার যন্ত্রে দেখে নিশ্চিত করুন।"}</SiteText></p>
    {data.sender_email && <p><SiteText>{"Amazon-এর অনুমোদিত প্রেরকের তালিকায় "}</SiteText><strong lang="en">{data.sender_email}</strong><SiteText>{" যোগ করুন।"}</SiteText></p>}
    {!data.configured && <p className="notice"><SiteText>{"কিন্ডলে পাঠানোর সেবা এখন প্রস্তুত নয়। পরিচালকের সঙ্গে যোগাযোগ করুন।"}</SiteText></p>}
    {!data.recipients.length && <p className="notice"><SiteText>{"আগে "}</SiteText><Link className="text-link" href="/profile/"><SiteText>{"প্রোফাইলে কিন্ডলের ঠিকানা যোগ করুন"}</SiteText></Link>।</p>}
    {options.isError && <p className="field-error" role="alert"><SiteText>{"বর্তমান তথ্য পাওয়া যায়নি।"}</SiteText></p>}
    <KindleRequestForm key={data.asset_revision + data.recipients.join(",")} options={data} /></div>;
}
