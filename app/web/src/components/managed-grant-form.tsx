"use client";

import { SiteFieldErrors } from "./site-field-errors";

import { AdminText } from "@/components/admin-language";
import { useRef, useState } from "react";
import { createManagedGrant } from "@/api/managed-access";
import type { ManagedAccount, ManagedGrant, ManagedGrantCreate } from "@/api/types";
import { accessScopes, scopedAccess, targetKinds } from "@/lib/access-status";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";
import { AccessTargetSelector } from "./access-target-selector";

function grantValues(fields: FormData, id: string): ManagedGrantCreate {
  const kind = String(fields.get("kind")), target = String(fields.get("target") ?? "");
  const expiry = String(fields.get("expires_at") ?? "");
  return { id, scope: String(fields.get("scope")) as ManagedGrantCreate["scope"], notes: String(fields.get("notes") ?? ""),
    expires_at: expiry ? new Date(expiry).toISOString() : null,
    ...(kind === "book" ? { book: target } : kind === "category" ? { category: target } : kind === "author" ? { contributor: target } : {}) };
}

export function ManagedGrantForm({ account, onSaved }: { account: ManagedAccount; onSaved: (grant: ManagedGrant) => Promise<void> }) {
  const identifier = useRef<string | null>(null);
  const [kind, setKind] = useState<keyof typeof targetKinds>("account");
  const [scope, setScope] = useState<ManagedGrantCreate["scope"]>("read:durable");
  const form = useManagedForm((values: ManagedGrantCreate) => createManagedGrant(account.id, values), onSaved);
  const shownScopes = Object.entries(accessScopes).filter(([value]) => kind === "account" || scopedAccess.has(value as ManagedGrantCreate["scope"]));
  return <form className="account-section access-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); const element = event.currentTarget; identifier.current ??= crypto.randomUUID();
    form.saving.mutate(grantValues(new FormData(element), identifier.current), { onSuccess: () => { identifier.current = null; element.reset(); setKind("account"); setScope("read:durable"); } });
  }}><h2><AdminText>{"অনুমতি যোগ করুন"}</AdminText></h2><p><AdminText>{"অনুমতি নির্দিষ্ট বই, বিভাগ বা লেখকের বইয়ের জন্য দিতে পারেন। সব বই বেছে নিলে হিসাবজুড়ে প্রযোজ্য হবে।"}</AdminText></p>
    <div className="form-field"><label htmlFor="grant-kind"><AdminText>{"অনুমতির পরিধি"}</AdminText></label><select id="grant-kind" name="kind" value={kind} disabled={form.blocked} onChange={(event) => { const next = event.target.value as keyof typeof targetKinds; setKind(next); if (next !== "account" && !scopedAccess.has(scope)) setScope("read:durable"); }}>
      {Object.entries(targetKinds).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}</select></div>
    {kind !== "account" && <AccessTargetSelector key={kind} kind={kind} disabled={form.blocked} errors={form.errors[kind === "author" ? "contributor" : kind]} />}
    <div className="form-field"><label htmlFor="grant-scope"><AdminText>{"যে কাজের অনুমতি"}</AdminText></label><select id="grant-scope" name="scope" value={scope} aria-invalid={!!form.errors.scope?.length} aria-describedby={form.errors.scope?.length ? "grant-scope-error" : undefined} disabled={form.blocked} onChange={(event) => setScope(event.target.value as ManagedGrantCreate["scope"])}>{shownScopes.map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}</select>
      {form.errors.scope?.length ? <p id="grant-scope-error" className="field-error" role="alert"><SiteFieldErrors errors={form.errors.scope} /></p> : null}</div>
    <div className="form-field"><label htmlFor="grant-expiry"><AdminText>{"মেয়াদ শেষ (আপনার স্থানীয় সময়, ঐচ্ছিক)"}</AdminText></label><input id="grant-expiry" name="expires_at" type="datetime-local" max="9999-12-31T23:59" aria-invalid={!!form.errors.expires_at?.length} aria-describedby={form.errors.expires_at?.length ? "grant-expiry-error" : undefined} disabled={form.blocked} />
      {form.errors.expires_at?.length ? <p id="grant-expiry-error" className="field-error" role="alert"><SiteFieldErrors errors={form.errors.expires_at} /></p> : null}</div>
    <AccountField name="notes" label="অনুমতির মন্তব্য" multiline maxLength={2000} errors={form.errors.notes} disabled={form.blocked} />
    {form.errors.non_field_errors?.length ? <p className="field-error" role="alert"><SiteFieldErrors errors={form.errors.non_field_errors} /></p> : null}
    <AccountFeedback error={form.saving.error} conflictMessage="অনুমতি বা অনুরোধের অবস্থা বদলেছে। তালিকার বর্তমান তথ্য দেখে সিদ্ধান্ত নিন।" />
    <div className="account-actions"><button className="button" disabled={form.blocked}><AdminText>{"অনুমতি যোগ করুন"}</AdminText></button>{form.saving.error && <button className="button button-quiet" type="button" disabled={form.saving.isPending} onClick={reloadManagedForm}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}</div>
    {form.saving.isSuccess && <p role="status"><AdminText>{"অনুমতি সংরক্ষিত হয়েছে।"}</AdminText></p>}</form>;
}
