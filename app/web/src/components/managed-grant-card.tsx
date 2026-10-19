"use client";

import { AdminDate, AdminText } from "@/components/admin-language";
import { useRef } from "react";
import { updateManagedGrant } from "@/api/managed-access";
import type { ManagedGrant, ManagedGrantUpdate } from "@/api/types";
import { accessScopes } from "@/lib/access-status";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { dhakaDateTimeParts, dhakaDateTimeValue } from "@/lib/bulk-access";
import { AccountFeedback } from "./account-feedback";
import { AccountField } from "./account-field";
import { AccessExpiryInput } from "./access-expiry-input";

export function ManagedGrantCard({ grant, editable, onSaved }: { grant: ManagedGrant; editable: boolean; onSaved: (grant: ManagedGrant) => Promise<void> }) {
  const revision = useRef(grant.updated_at);
  const form = useManagedForm((values: ManagedGrantUpdate) => updateManagedGrant(grant.user, grant.id, values), async (updated) => { revision.current = updated.updated_at; await onSaved(updated); });
  const scope = Object.hasOwn(accessScopes, grant.scope) ? accessScopes[grant.scope as keyof typeof accessScopes] : "রক্ষণাবেক্ষণের অনুমতি";
  return <li className="job-card" data-grant-id={grant.id}><div className="job-heading"><h3><AdminText>{scope}</AdminText></h3><span className="status-label"><AdminText>{grant.effective ? "কার্যকর" : grant.is_active ? "মেয়াদ শেষ" : "প্রত্যাহৃত"}</AdminText></span></div>
    <p><AdminText>{"পরিধি: "}</AdminText>{grant.target_type === "account" ? <AdminText>{"সব বই"}</AdminText> : grant.target_label}</p><p className="muted"><AdminText>{"মেয়াদ শেষ: "}</AdminText>{grant.expires_at ? <AdminDate value={grant.expires_at} /> : <AdminText>{"নির্দিষ্ট নয়"}</AdminText>}</p>
    {editable && Object.hasOwn(accessScopes, grant.scope) ? <form onChange={form.markDirty} onReset={form.discard} onSubmit={(event) => {
      event.preventDefault(); const fields = new FormData(event.currentTarget);
      const date = String(fields.get(`expiry-${grant.id}-date`) ?? ""), time = String(fields.get(`expiry-${grant.id}-time`) ?? "02:00");
      const current = dhakaDateTimeParts(grant.expires_at);
      form.saving.mutate({ expected_updated_at: revision.current, notes: String(fields.get(`grant-note-${grant.id}`)), ...(date === current.date && time === current.time ? {} : { expires_at: dhakaDateTimeValue(date, time) }) });
    }}><details><summary><AdminText>{"মন্তব্য বা মেয়াদ বদলান"}</AdminText></summary><AccountField name={`grant-note-${grant.id}`} label="মন্তব্য" initial={grant.notes} multiline maxLength={2000} disabled={form.blocked} />
      <AccessExpiryInput name={`expiry-${grant.id}`} initial={grant.expires_at} disabled={form.blocked} />
      <button className="button button-quiet" disabled={form.blocked}><AdminText>{"অনুমতির তথ্য সংরক্ষণ করুন"}</AdminText></button></details>
      <AccountFeedback error={form.saving.error} />{Object.values(form.errors).flat().map((error, index) => <p key={index} role="alert" className="field-error">{error}</p>)}
      <div className="account-actions"><button type="button" className="button button-quiet" disabled={form.blocked || form.dirty} onClick={() => form.saving.mutate({ expected_updated_at: revision.current, is_active: !grant.is_active })}><AdminText>{grant.is_active ? "অনুমতি প্রত্যাহার করুন" : "অনুমতি ফিরিয়ে দিন"}</AdminText></button>
        {form.dirty && !form.saving.error && <button type="reset" className="button button-quiet" disabled={form.saving.isPending}><AdminText>{"লেখা বাদ দিন"}</AdminText></button>}
        {form.saving.error && <button type="button" className="button button-quiet" onClick={reloadManagedForm} disabled={form.saving.isPending}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}</div></form> : <p>{grant.notes}</p>}
  </li>;
}
