"use client";

import { SiteText } from "@/components/site-language";

import { useMutation } from "@tanstack/react-query";
import { disableTOTP, startTOTP } from "@/api/account";
import type { TOTPSetup } from "@/api/types";
import { useSecurityForm } from "@/lib/security-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";
import { SecurityCodeField } from "./security-code-field";

export function StartSecurityForm({ onStarted, onCancel }: { onStarted: (setup: TOTPSetup) => void; onCancel: () => void }) {
  const start = useMutation({ mutationFn: startTOTP, onSuccess: onStarted, retry: false, gcTime: 0 });
  const form = useSecurityForm(start);
  return <form onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); start.mutate(String(new FormData(event.currentTarget).get("security_password")));
  }}><p><SiteText>{"সেটআপ শুরু বা আবার খুলতে আপনার পাসওয়ার্ড দিন।"}</SiteText></p>
    <AccountField name="security_password" label="পাসওয়ার্ড দিয়ে নিশ্চিত করুন" type="password" autoComplete="current-password" required maxLength={4096} errors={form.errors.current_password} />
    <AccountFeedback error={start.error} /><div className="account-actions"><button className="button" disabled={start.isPending}><SiteText>{"সেটআপ খুলুন"}</SiteText></button>
      <button className="button button-quiet" type="button" onClick={onCancel} disabled={start.isPending}><SiteText>{"ফিরে যান"}</SiteText></button></div>
  </form>;
}

export function DisableSecurityForm({ onDisabled, onCancel }: { onDisabled: () => Promise<void>; onCancel: () => void }) {
  const disabling = useMutation({ mutationFn: disableTOTP, onSuccess: onDisabled, retry: false, gcTime: 0 });
  const form = useSecurityForm(disabling);
  return <form onChange={form.markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    disabling.mutate({ current_password: String(fields.get("disable_password")), token: String(fields.get("token")) });
  }}><p><SiteText>{"বন্ধ করতে পাসওয়ার্ড ও অ্যাপের একটি নতুন কোড দিন।"}</SiteText></p>
    <AccountField name="disable_password" label="পাসওয়ার্ড দিয়ে নিশ্চিত করুন" type="password" autoComplete="current-password" required maxLength={4096} errors={form.errors.current_password} />
    <SecurityCodeField errors={form.errors.token} /><AccountFeedback error={disabling.error} /><div className="account-actions">
      <button className="button" disabled={disabling.isPending}><SiteText>{"দুই ধাপের নিরাপত্তা বন্ধ করুন"}</SiteText></button><button className="button button-quiet" type="button" disabled={disabling.isPending} onClick={onCancel}><SiteText>{"ফিরে যান"}</SiteText></button></div>
  </form>;
}
