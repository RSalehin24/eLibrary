"use client";

import { AdminText } from "@/components/admin-language";
import { useRef } from "react";
import { updateManagedAccount } from "@/api/managed-access";
import type { ManagedAccount, ManagedAccountUpdate } from "@/api/types";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";

export function ManagedAccountForm({ account, onSaved }: { account: ManagedAccount; onSaved: (account: ManagedAccount) => Promise<void> }) {
  const revision = useRef(account.updated_at);
  const form = useManagedForm((values: ManagedAccountUpdate) => updateManagedAccount(account.id, values), async (updated) => { revision.current = updated.updated_at; await onSaved(updated); });
  return <form className="account-section" onChange={form.markDirty} onReset={form.discard} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    form.saving.mutate({ expected_updated_at: revision.current, full_name: String(fields.get("full_name")), is_active: fields.has("is_active"), totp_required: fields.has("totp_required") });
  }}><h2><AdminText>{"হিসাবের তথ্য"}</AdminText></h2><p><AdminText>{"ইমেইল: "}</AdminText><span lang="en" className="kindle-address">{account.email}</span></p>
    <AccountField name="full_name" label="পাঠকের নাম" initial={account.full_name} errors={form.errors.full_name} maxLength={255} disabled={form.blocked} />
    <label className="checkbox-field"><input name="is_active" type="checkbox" defaultChecked={account.is_active} disabled={form.blocked} /><AdminText>{"হিসাব সক্রিয়"}</AdminText></label>
    <div id="account-security"><label className="checkbox-field"><input name="totp_required" type="checkbox" defaultChecked={account.totp_required} disabled={form.blocked} /><AdminText>{"দুই ধাপে প্রবেশ আবশ্যক"}</AdminText></label></div>
    <p className="muted"><AdminText>{"হিসাব নিষ্ক্রিয় করলে পাঠক প্রবেশ ও ব্যক্তিগত কাজ করতে পারবেন না। দুই ধাপ আবশ্যক করলে প্রস্তুতি শেষ না করা পর্যন্ত ব্যক্তিগত কাজ বন্ধ থাকবে।"}</AdminText></p>
    <AccountFeedback error={form.saving.error} /><div className="account-actions"><button className="button" disabled={form.blocked}><AdminText>{"হিসাব সংরক্ষণ করুন"}</AdminText></button>
      {form.dirty && !form.saving.error && <button className="button button-quiet" type="reset" disabled={form.saving.isPending}><AdminText>{"লেখা বাদ দিন"}</AdminText></button>}
      {form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm} disabled={form.saving.isPending}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}</div>
    {form.saving.isSuccess && <p role="status"><AdminText>{"হিসাবের পরিবর্তন সংরক্ষিত হয়েছে।"}</AdminText></p>}</form>;
}
