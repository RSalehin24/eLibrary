"use client";

import Link from "next/link";
import { requestPasswordReset } from "@/api/account-mail";
import type { PasswordResetRequest } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";

export function PasswordResetForm() {
  const form = useManagedForm((values: PasswordResetRequest) => requestPasswordReset(values), async () => {});
  if (form.saving.isSuccess) return <section className="account-form"><h1>ইমেইল পরীক্ষা করুন</h1><p>এই ইমেইলে উপযুক্ত হিসাব থাকলে পাসওয়ার্ড বদলানোর লিংক পাঠানো হবে। স্প্যাম ফোল্ডারও পরীক্ষা করুন।</p>
    <p>কয়েক মিনিট সময় দিন। আমন্ত্রণের পাসওয়ার্ড এখনো তৈরি না হলে সর্বশেষ আমন্ত্রণের লিংক ব্যবহার করুন।</p><Link className="button" href="/login/">প্রবেশের পাতায় ফিরুন</Link></section>;
  return <form className="account-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); form.saving.mutate({ email: String(new FormData(event.currentTarget).get("email")) });
  }}><h1>পাসওয়ার্ড ভুলে গেছেন?</h1><p>অ্যাকাউন্টের ইমেইল দিন। পাসওয়ার্ড পরিবর্তনের লিংক ইমেইলে পাঠানো হবে।</p>
    <AccountField name="email" label="অ্যাকাউন্টের ইমেইল" type="email" autoComplete="email" maxLength={254} required disabled={form.blocked} errors={form.errors.email} />
    <AccountFeedback error={form.saving.error} />{form.saving.error && <p className="muted">অনুরোধের ফল নিশ্চিত না হলে আগে ইমেইল পরীক্ষা করুন। পরে এই পাতা আবার খুলে নতুন অনুরোধ করতে পারবেন।</p>}
    <button className="button" disabled={form.blocked}>পাসওয়ার্ড বদলানোর লিংক চাই</button><Link className="text-link" href="/login/">প্রবেশের পাতায় ফিরুন →</Link></form>;
}
