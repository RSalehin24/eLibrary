"use client";

import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { useState } from "react";
import { inviteAccount } from "@/api/account-mail";
import { createManagedAccount } from "@/api/managed-access";
import type { Invitation, ManagedAccountCreate } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";
import { InitialPasswordFields } from "./initial-password-fields";
import { useAdminLanguage } from "./admin-language";

type CreationCommand = { method: "invite"; values: Invitation } | { method: "password"; values: ManagedAccountCreate };
async function saveAccount(command: CreationCommand) {
  return command.method === "invite" ? { method: "invite" as const, data: await inviteAccount(command.values) } : { method: "password" as const, data: await createManagedAccount(command.values) };
}

export function InvitationForm({ canSetPassword = false }: { canSetPassword?: boolean }) {
  const { t } = useAdminLanguage();
  const [operation, setOperation] = useState<string | null>(null), [method, setMethod] = useState<"invite" | "password">("invite");
  const form = useManagedForm(saveAccount, async () => {});
  const saved = form.saving.data;
  if (form.saving.isSuccess && saved?.method === "password") return <section className="account-form"><h1>{t("পাঠকের অ্যাকাউন্ট তৈরি হয়েছে")}</h1><p>{t("পাঠক এখন পাসওয়ার্ড দিয়ে প্রবেশ করতে পারবেন। অ্যাকাউন্টের পাতায় প্রয়োজনীয় অনুমতি দিন।")}</p><Link className="button" href={`/manage/users-access/${saved.data.id}/`}>{t("অ্যাকাউন্ট ও অনুমতি দেখুন")}</Link></section>;
  if (form.saving.isSuccess && saved?.method === "invite") return <section className="account-form"><h1><AdminText>{"আমন্ত্রণের অনুরোধ সংরক্ষিত হয়েছে"}</AdminText></h1><p><AdminText>{"ইমেইল পাঠানোর কাজ অপেক্ষমাণ। পাঠকের হিসাব ও অনুমতি এখন পরিচালনা করতে পারবেন।"}</AdminText></p>
    <Link className="button" href={`/manage/users-access/mail/${saved.data.operation_id}/`}><AdminText>{"আমন্ত্রণের অবস্থা দেখুন"}</AdminText></Link></section>;
  return <form className="account-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget), identifier = operation ?? crypto.randomUUID(); setOperation(identifier);
    const values = { operation_id: identifier, email: String(fields.get("email")), full_name: String(fields.get("full_name")), totp_required: fields.has("totp_required") };
    form.saving.mutate(method === "invite" ? { method, values } : { method, values: { ...values, is_active: fields.has("is_active"), password: String(fields.get("password")), confirm_password: String(fields.get("confirm_password")) } });
  }}><h1>{t(canSetPassword ? "পাঠক যোগ করুন" : "পাঠককে আমন্ত্রণ জানান")}</h1><p>{t(method === "invite" ? "পাঠক ইমেইলের লিংক দিয়ে নিজের পাসওয়ার্ড তৈরি করবেন। পরে হিসাবের পাতায় প্রয়োজনীয় অনুমতি দিন।" : "প্রাথমিক পাসওয়ার্ড দিয়ে অ্যাকাউন্ট তৈরি করুন। এরপর প্রয়োজনীয় অনুমতি দিন।")}</p>
    {canSetPassword && <div className="form-field"><label htmlFor="account-setup-method">{t("অ্যাকাউন্ট তৈরির পদ্ধতি")}</label><select id="account-setup-method" value={method} onChange={(event) => { setMethod(event.target.value as "invite" | "password"); setOperation(null); form.saving.reset(); }} disabled={form.blocked}><option value="invite">{t("ইমেইলে পাসওয়ার্ড তৈরির লিংক পাঠান")}</option><option value="password">{t("এখনই প্রাথমিক পাসওয়ার্ড দিন")}</option></select></div>}
    <AccountField name="email" label="পাঠকের ইমেইল" type="email" autoComplete="off" maxLength={254} required disabled={form.blocked} errors={form.errors.email} />
    <AccountField name="full_name" label="পাঠকের নাম" maxLength={255} disabled={form.blocked} errors={form.errors.full_name} />
    {method === "password" && <InitialPasswordFields disabled={form.blocked} errors={form.errors} />}
    {method === "password" && <label className="checkbox-field"><input name="is_active" type="checkbox" defaultChecked disabled={form.blocked} /><AdminText>{"হিসাব সক্রিয়"}</AdminText></label>}
    <label className="checkbox-field"><input name="totp_required" type="checkbox" disabled={form.blocked} /><AdminText>{"দুই ধাপে প্রবেশ আবশ্যক"}</AdminText></label>
    <AccountFeedback error={form.saving.error} /><button className="button" disabled={form.blocked}>{t(method === "password" ? "অ্যাকাউন্ট তৈরি করুন" : "আমন্ত্রণ পাঠানোর অনুরোধ করুন")}</button>
    {form.saving.error && operation && method === "invite" && <p><Link className="text-link" href={`/manage/users-access/mail/${operation}/`}><AdminText>{"এই অনুরোধের অবস্থা দেখুন →"}</AdminText></Link></p>}
    <Link className="text-link" href="/manage/users-access/"><AdminText>{"← ব্যবহারকারীর তালিকায় ফিরুন"}</AdminText></Link></form>;
}
