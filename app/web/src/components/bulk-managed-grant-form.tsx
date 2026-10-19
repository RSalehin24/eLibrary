"use client";

import { useRef, useState } from "react";
import { createManagedGrants } from "@/api/bulk-managed-access";
import type { ManagedAccount, ManagedGrantBulkResult, ManagedGrantCreate } from "@/api/types";
import { accessScopes, scopedAccess } from "@/lib/access-status";
import { bulkGrantCount, bulkGrantEntries, dhakaDateTimeValue, maximumBulkGrants, toggleAccessScope, type BulkAccessKind, type BulkAccessSelection, type BulkAccessTarget } from "@/lib/bulk-access";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { AccountField } from "./account-field";
import { AccessExpiryInput } from "./access-expiry-input";
import { AdminNumber, AdminText } from "./admin-language";
import { BulkAccessResults } from "./bulk-access-results";
import { BulkAccessTargets } from "./bulk-access-targets";
import { SiteFieldErrors } from "./site-field-errors";
import "./bulk-access.css";

export function BulkManagedGrantForm({ account, onSaved }: { account: ManagedAccount; onSaved: () => Promise<void> }) {
  const [kind, setKind] = useState<BulkAccessKind>("book");
  const [scopes, setScopes] = useState<ManagedGrantCreate["scope"][]>(["read:durable"]);
  const [targets, setTargets] = useState<BulkAccessTarget[]>([]);
  const [result, setResult] = useState<{ response: ManagedGrantBulkResult; requests: ManagedGrantCreate[]; targets: BulkAccessTarget[] } | null>(null);
  const command = useRef<{ signature: string; entries: ManagedGrantCreate[]; targets: BulkAccessTarget[] } | null>(null);
  const form = useManagedForm((entries: ManagedGrantCreate[]) => createManagedGrants(account.id, entries), async (output) => { if (command.current) setResult({ response: output, requests: command.current.entries, targets: command.current.targets }); await onSaved(); });
  const count = bulkGrantCount({ kind, scopes, targets });
  function submit(element: HTMLFormElement) {
    const fields = new FormData(element);
    const selection: BulkAccessSelection = { kind, scopes, targets, notes: String(fields.get("bulk-note") ?? ""), expiresAt: dhakaDateTimeValue(String(fields.get("bulk-expiry-date") ?? ""), String(fields.get("bulk-expiry-time") ?? "02:00")) };
    const signature = JSON.stringify(selection);
    if (command.current?.signature !== signature) command.current = { signature, entries: bulkGrantEntries(selection, () => crypto.randomUUID()), targets: [...targets] };
    form.saving.mutate(command.current.entries);
  }
  return <form className="account-section bulk-access" onChange={form.markDirty} onSubmit={(event) => { event.preventDefault(); submit(event.currentTarget); }}>
    <h2><AdminText>{"একসঙ্গে একাধিক অনুমতি দিন"}</AdminText></h2>
    <p><AdminText>{"যার জন্য: "}</AdminText><strong>{account.full_name || account.email}</strong><span className="muted"> · {account.email}</span></p>
    <p><AdminText>{"একাধিক বই, বিভাগ বা লেখক এবং একাধিক কাজের অনুমতি একসঙ্গে দিন। প্রতিটি অনুমতির ফল আলাদা দেখাবে।"}</AdminText></p>
    <fieldset disabled={form.blocked}><legend><AdminText>{"১. কোন ধরনের বইয়ের জন্য"}</AdminText></legend>
      <label htmlFor="bulk-access-kind"><AdminText>{"একাধিক অনুমতির পরিধি"}</AdminText></label><select id="bulk-access-kind" value={kind} onChange={(event) => { const value = event.target.value as BulkAccessKind; setKind(value); setTargets([]); if (value !== "account") setScopes((previous) => previous.filter((scope) => scopedAccess.has(scope))); }}>
        {Object.entries({ account: "সব বই", book: "বই", category: "বিভাগ", author: "লেখক" }).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}
      </select>
    </fieldset>
    {kind !== "account" && <BulkAccessTargets key={kind} kind={kind} selected={targets} disabled={form.blocked} onChange={(selection) => { setTargets(selection); form.markDirty(); }} />}
    <fieldset disabled={form.blocked}><legend><AdminText>{"৩. যে কাজগুলোর অনুমতি দেবেন"}</AdminText></legend><div className="bulk-access-scopes">
      {Object.entries(accessScopes).filter(([scope]) => kind === "account" || scopedAccess.has(scope as ManagedGrantCreate["scope"])).map(([scope, label]) => <label className="check-field" key={scope}><input type="checkbox" checked={scopes.includes(scope as ManagedGrantCreate["scope"])} onChange={() => setScopes((previous) => toggleAccessScope(previous, scope as ManagedGrantCreate["scope"]))} /><AdminText>{label}</AdminText></label>)}
    </div><p className="muted"><AdminText>{"একবার পড়া এবং স্থায়ী পড়ার অনুমতি একসঙ্গে দেওয়া যায় না।"}</AdminText></p></fieldset>
    <AccessExpiryInput name="bulk-expiry" disabled={form.blocked} />
    <AccountField name="bulk-note" label="একাধিক অনুমতির মন্তব্য" multiline maxLength={2000} disabled={form.blocked} />
    <p className="bulk-access-summary"><AdminNumber value={scopes.length} /><AdminText>{"টি কাজ × "}</AdminText><AdminNumber value={kind === "account" ? 1 : targets.length} /><AdminText>{"টি লক্ষ্য = "}</AdminText><AdminNumber value={count} /><AdminText>{"টি অনুমতি"}</AdminText></p>
    {count > maximumBulkGrants && <p role="alert" className="field-error"><AdminText>{"একবারে সর্বোচ্চ ১০০টি অনুমতি দিন। কিছু নির্বাচন সরান।"}</AdminText></p>}
    <AccountFeedback error={form.saving.error} />
    {!!Object.values(form.errors).flat().length && <p role="alert" className="field-error"><SiteFieldErrors errors={Object.values(form.errors).flat()} /></p>}
    <div className="account-actions"><button className="button" disabled={form.blocked || count === 0 || count > maximumBulkGrants}><AdminText>{form.saving.isPending ? "অনুমতি সংরক্ষণ হচ্ছে…" : "নির্বাচিত অনুমতি যোগ করুন"}</AdminText></button>
      {form.saving.error && <button type="button" className="button button-quiet" disabled={form.saving.isPending} onClick={reloadManagedForm}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}</div>
    {result && <BulkAccessResults result={result.response} requests={result.requests} targets={result.targets} />}
  </form>;
}
