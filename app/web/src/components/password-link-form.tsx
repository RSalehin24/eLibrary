"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { confirmPasswordLink, inspectPasswordLinkURL } from "@/api/password-links";
import type { PasswordLinkConfirmation } from "@/api/types";
import { notifyAccountChange } from "@/lib/account-channel";
import { useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";

export function PasswordLinkForm() {
  const client = useQueryClient();
  const inspection = useMutation({ mutationFn: inspectPasswordLinkURL, retry: false, gcTime: 0 });
  const inspect = inspection.mutate;
  useEffect(() => {
    inspect(window.location.href); window.history.replaceState(null, "", window.location.pathname);
    const openNewLink = () => { if (window.location.hash) window.location.reload(); };
    window.addEventListener("hashchange", openNewLink);
    return () => window.removeEventListener("hashchange", openNewLink);
  }, [inspect]);
  const form = useManagedForm((values: PasswordLinkConfirmation) => confirmPasswordLink(values), async (result) => {
    if (result.next_step === "totp_setup") { notifyAccountChange(); client.removeQueries({ queryKey: ["private"] }); }
  });
  if (form.saving.isSuccess) return <section className="account-form"><h1>পাসওয়ার্ড সংরক্ষিত হয়েছে</h1><p>এই লিংকটি আর ব্যবহার করা যাবে না।</p>
    <Link className="button" href={form.saving.data.next_step === "totp_setup" ? "/profile/" : "/login/"}>{form.saving.data.next_step === "totp_setup" ? "দুই ধাপের নিরাপত্তা প্রস্তুত করুন" : "অ্যাকাউন্টে প্রবেশ করুন"}</Link></section>;
  return <form className="account-form" onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); if (!inspection.data) return;
    const fields = new FormData(event.currentTarget); form.saving.mutate({ ...inspection.data.ticket, new_password: String(fields.get("new_password")), confirm_new_password: String(fields.get("confirm_new_password")) });
  }}><p className="eyebrow">আপনার ব্যক্তিগত পাঠাগার</p><h1>{inspection.data?.inspection.purpose === "setup" ? "পাসওয়ার্ড তৈরি করুন" : "নতুন পাসওয়ার্ড দিন"}</h1>
    {inspection.isPending && <p role="status">লিংক পরীক্ষা করা হচ্ছে…</p>}
    {inspection.isError && <p role="alert" className="field-error">লিংকটি ব্যবহার করা যায়নি। অন্য হিসাবে প্রবেশ করা থাকলে আগে প্রস্থান করুন। এরপর ইমেইলের সর্বশেষ লিংকটি আবার খুলুন।</p>}
    {inspection.isSuccess && <><p>অন্তত ১২ অক্ষরের পাসওয়ার্ড দিন। সহজে অনুমান করা যায় এমন শব্দ বা শুধু সংখ্যা ব্যবহার করবেন না।</p>
      {inspection.data.inspection.totp_setup_required && <p className="notice">পাসওয়ার্ডের পরে দুই ধাপের নিরাপত্তা প্রস্তুত করতে হবে।</p>}
      <AccountField name="new_password" label="নতুন পাসওয়ার্ড" type="password" autoComplete="new-password" required minLength={12} maxLength={4096} disabled={form.blocked} errors={form.errors.new_password} />
      <AccountField name="confirm_new_password" label="নতুন পাসওয়ার্ড আবার লিখুন" type="password" autoComplete="new-password" required minLength={12} maxLength={4096} disabled={form.blocked} errors={form.errors.confirm_new_password} />
      {form.errors.token?.length ? <p role="alert" className="field-error">লিংকটি মেয়াদোত্তীর্ণ বা ইতিমধ্যে ব্যবহার হয়েছে। ইমেইলের সর্বশেষ লিংক খুলুন।</p> : <AccountFeedback error={form.saving.error} />}
      <button className="button" disabled={form.blocked}>পাসওয়ার্ড সংরক্ষণ করুন</button></>}
    <p className="muted">লিংকের ফল নিশ্চিত না হলে নতুন পাসওয়ার্ড দিয়ে প্রবেশ পরীক্ষা করুন। একই অনুরোধ স্বয়ংক্রিয়ভাবে আবার পাঠানো হবে না।</p>
    <Link className="text-link" href="/login/">প্রবেশের পাতায় ফিরুন →</Link></form>;
}
