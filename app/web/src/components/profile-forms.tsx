"use client";

import { SiteText } from "@/components/site-language";

import { useProfileForm, type ProfileFormProps } from "@/lib/profile-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";

export function ProfileIdentityForm(props: ProfileFormProps) {
  const { saving, errors, dirty, markDirty, discard } = useProfileForm(props);
  return <form className="account-section" onReset={discard} onChange={markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    saving.mutate({ full_name: String(fields.get("full_name")) });
  }}><h2><SiteText>{"আপনার পরিচয়"}</SiteText></h2><p><SiteText>{"ইমেইল: "}</SiteText><span lang="en">{props.profile.email}</span></p>
    <AccountField name="full_name" label="নাম" initial={props.profile.full_name ?? ""} maxLength={255} autoComplete="name" errors={errors.full_name} disabled={saving.isPending} />
    <AccountFeedback error={saving.error} /><div className="account-actions"><button className="button" disabled={saving.isPending}><SiteText>{"নাম সংরক্ষণ করুন"}</SiteText></button>{dirty && <button className="button button-quiet" type="reset" disabled={saving.isPending}><SiteText>{"লেখা বাদ দিন"}</SiteText></button>}</div>
  </form>;
}

export function ProfilePasswordForm(props: ProfileFormProps) {
  const { saving, errors, dirty, markDirty, discard } = useProfileForm(props);
  return <form className="account-section" onReset={discard} onChange={markDirty} onSubmit={(event) => {
    event.preventDefault(); const form = event.currentTarget; const fields = new FormData(form);
    saving.mutate({ current_password: String(fields.get("current_password")), new_password: String(fields.get("new_password")), confirm_new_password: String(fields.get("confirm_new_password")) }, { onSuccess: () => form.reset() });
  }}><h2><SiteText>{"পাসওয়ার্ড বদলান"}</SiteText></h2><p className="muted"><SiteText>{"অন্তত ১২ অক্ষরের পাসওয়ার্ড দিন। বদলানোর পরে অন্য সেশনে আবার প্রবেশ করতে হবে।"}</SiteText></p>
    <AccountField name="current_password" label="বর্তমান পাসওয়ার্ড" type="password" autoComplete="current-password" required maxLength={4096} errors={errors.current_password} disabled={saving.isPending} />
    <AccountField name="new_password" label="নতুন পাসওয়ার্ড" type="password" autoComplete="new-password" minLength={12} maxLength={4096} required errors={errors.new_password} disabled={saving.isPending} />
    <AccountField name="confirm_new_password" label="নতুন পাসওয়ার্ড আবার লিখুন" type="password" autoComplete="new-password" minLength={12} maxLength={4096} required errors={errors.confirm_new_password} disabled={saving.isPending} />
    <AccountFeedback error={saving.error} /><div className="account-actions"><button className="button" disabled={saving.isPending}><SiteText>{"পাসওয়ার্ড বদলান"}</SiteText></button>{dirty && <button className="button button-quiet" type="reset" disabled={saving.isPending}><SiteText>{"লেখা বাদ দিন"}</SiteText></button>}</div>
  </form>;
}

export function ProfileKindleForm(props: ProfileFormProps) {
  const { saving, errors, dirty, markDirty, discard } = useProfileForm(props);
  return <form className="account-section" onReset={discard} onChange={markDirty} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    saving.mutate({ kindle_emails: String(fields.get("kindle_emails")).split(/[\n,;]/).map((email) => email.trim()).filter(Boolean) });
  }}><h2><SiteText>{"কিন্ডলের ঠিকানা"}</SiteText></h2><p className="muted"><SiteText>{"প্রতি লাইনে একটি Kindle ইমেইল লিখুন। সর্বোচ্চ ১০টি ঠিকানা রাখা যাবে।"}</SiteText></p>
    {props.profile.kindle_sender_email && <p><SiteText>{"Amazon-এর অনুমোদিত প্রেরকের তালিকায় "}</SiteText><span lang="en">{props.profile.kindle_sender_email}</span><SiteText>{" যোগ করুন।"}</SiteText></p>}
    <AccountField name="kindle_emails" label="Kindle ইমেইল ঠিকানা" initial={props.profile.kindle_emails.join("\n")} multiline maxLength={3200} errors={errors.kindle_emails} disabled={saving.isPending} />
    <AccountFeedback error={saving.error} /><div className="account-actions"><button className="button" disabled={saving.isPending}><SiteText>{"ঠিকানা সংরক্ষণ করুন"}</SiteText></button>{dirty && <button className="button button-quiet" type="reset" disabled={saving.isPending}><SiteText>{"লেখা বাদ দিন"}</SiteText></button>}</div>
  </form>;
}
