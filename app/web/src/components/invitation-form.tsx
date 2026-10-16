"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useState } from "react";
import { inviteAccount } from "@/api/account-mail";
import type { Invitation } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";

export function InvitationForm() {
  const [operation, setOperation] = useState<string | null>(null);
  const form = useManagedForm((values: Invitation) => inviteAccount(values), async () => {});
  if (form.saving.isSuccess) return <section className="account-form"><h1><AdminText>{"আমন্ত্রণের অনুরোধ সংরক্ষিত হয়েছে"}</AdminText></h1><p><AdminText>{"ইমেইল পাঠানোর কাজ অপেক্ষমাণ। পাঠকের হিসাব ও অনুমতি এখন পরিচালনা করতে পারবেন।"}</AdminText></p>
    <Link className="button" href={`/manage/users-access/mail/${form.saving.data.operation_id}/`}><AdminText>{"আমন্ত্রণের অবস্থা দেখুন"}</AdminText></Link></section>;
  return <form className="account-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget), identifier = operation ?? crypto.randomUUID(); setOperation(identifier);
    form.saving.mutate({ operation_id: identifier, email: String(fields.get("email")), full_name: String(fields.get("full_name")), totp_required: fields.has("totp_required") });
  }}><h1><AdminText>{"পাঠককে আমন্ত্রণ জানান"}</AdminText></h1><p><AdminText>{"পাঠক ইমেইলের লিংক দিয়ে নিজের পাসওয়ার্ড তৈরি করবেন। পরে হিসাবের পাতায় প্রয়োজনীয় অনুমতি দিন।"}</AdminText></p>
    <AccountField name="email" label="পাঠকের ইমেইল" type="email" autoComplete="off" maxLength={254} required disabled={form.blocked} errors={form.errors.email} />
    <AccountField name="full_name" label="পাঠকের নাম" maxLength={255} disabled={form.blocked} errors={form.errors.full_name} />
    <label className="checkbox-field"><input name="totp_required" type="checkbox" disabled={form.blocked} /><AdminText>{"দুই ধাপে প্রবেশ আবশ্যক"}</AdminText></label>
    <AccountFeedback error={form.saving.error} /><button className="button" disabled={form.blocked}><AdminText>{"আমন্ত্রণ পাঠানোর অনুরোধ করুন"}</AdminText></button>
    {form.saving.error && operation && <p><Link className="text-link" href={`/manage/users-access/mail/${operation}/`}><AdminText>{"এই অনুরোধের অবস্থা দেখুন →"}</AdminText></Link></p>}
    <Link className="text-link" href="/manage/users-access/"><AdminText>{"← ব্যবহারকারীর তালিকায় ফিরুন"}</AdminText></Link></form>;
}
