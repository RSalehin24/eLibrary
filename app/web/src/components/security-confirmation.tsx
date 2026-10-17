"use client";

import { SiteText, SiteNextImage } from "@/components/site-language";

import { useMutation } from "@tanstack/react-query";
import { cancelTOTP, confirmTOTP } from "@/api/account";
import type { TOTPSetup } from "@/api/types";
import { useSecurityForm } from "@/lib/security-form";
import { useUpdateParticipant } from "@/lib/update-safety";
import { AccountFeedback } from "./account-feedback";
import { SecurityCodeField } from "./security-code-field";

export function SecurityConfirmation({ setup, onConfirmed, onCancelled }: { setup: TOTPSetup; onConfirmed: () => Promise<void>; onCancelled: () => Promise<void> }) {
  const confirming = useMutation({ mutationFn: confirmTOTP, onSuccess: onConfirmed, retry: false, gcTime: 0 });
  const cancelling = useMutation({ mutationFn: cancelTOTP, onSuccess: onCancelled, retry: false, gcTime: 0 });
  const form = useSecurityForm(confirming);
  useUpdateParticipant({ dirty: true });
  return <div><p><SiteText>{"Authenticator অ্যাপে QR কোডটি স্ক্যান করুন অথবা সেটআপের চাবি লিখুন। কোড দিয়ে নিশ্চিত করার পরে নিরাপত্তা চালু হবে।"}</SiteText></p>
    <SiteNextImage unoptimized className="authenticator-qr" src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(setup.qr_svg)}`} alt="Authenticator সেটআপের QR কোড" width={240} height={240} />
    <p><SiteText>{"সেটআপের চাবি: "}</SiteText><code className="authenticator-secret" data-testid="authenticator-secret">{setup.secret}</code></p>
    <p className="muted"><SiteText>{"এই চাবি ব্যক্তিগতভাবে রাখুন। এটি অন্য কাউকে দেবেন না।"}</SiteText></p>
    <form onChange={form.markDirty} onSubmit={(event) => { event.preventDefault(); confirming.mutate(String(new FormData(event.currentTarget).get("token"))); }}>
      <SecurityCodeField errors={form.errors.token} /><AccountFeedback error={confirming.error ?? cancelling.error} />
      <div className="account-actions"><button className="button" disabled={confirming.isPending || cancelling.isPending}><SiteText>{"কোড নিশ্চিত করুন"}</SiteText></button>
        <button className="button button-quiet" type="button" disabled={confirming.isPending || cancelling.isPending} onClick={() => cancelling.mutate()}><SiteText>{"সেটআপ বাতিল করুন"}</SiteText></button></div>
    </form>
  </div>;
}
