"use client";

import Image from "next/image";
import { useRef, useState } from "react";
import { uploadProfileImage, removeProfileImage } from "@/api/account";
import type { ProfileFormProps } from "@/lib/profile-form";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";

export function ProfileImageForm({ profile, onSaved }: ProfileFormProps) {
  const element = useRef<HTMLFormElement>(null);
  const [image, setImage] = useState<File | null>(null);
  const form = useManagedForm((file: File | null) => file ? uploadProfileImage(file, profile.updated_at) : removeProfileImage(profile.updated_at), async (updated) => { setImage(null); element.current?.reset(); await onSaved(updated); });
  return <form ref={element} className="account-section" onSubmit={(event) => { event.preventDefault(); if (image && !form.blocked) form.saving.mutate(image); }}><h2>প্রোফাইলের ছবি</h2>
    {profile.profile_image_url && <Image src={profile.profile_image_url} alt="আপনার প্রোফাইলের ছবি" width={128} height={128} unoptimized style={{ objectFit: "cover", borderRadius: "50%" }} />}
    <p className="muted">PNG, JPEG বা WebP; সর্বোচ্চ ৫ MiB এবং ২০৪৮×২০৪৮ পিক্সেল। ছবির অতিরিক্ত তথ্য বাদ দিয়ে ছোট আকারে রাখা হবে।</p>
    <div className="form-field"><label htmlFor="profile-image">নতুন প্রোফাইলের ছবি</label><input id="profile-image" type="file" accept="image/png,image/jpeg,image/webp" disabled={form.blocked} aria-invalid={!!form.errors.image} aria-describedby={form.errors.image ? "profile-image-error" : undefined} onChange={(event) => { setImage(event.target.files?.[0] ?? null); form.markDirty(); }} />{form.errors.image && <p id="profile-image-error" className="field-error">{form.errors.image.join(" ")}</p>}</div>
    <AccountFeedback error={form.saving.error} />
    <div className="account-actions"><button className="button" disabled={!image || form.blocked}>ছবি সংরক্ষণ করুন</button>
      {profile.profile_image_url && <button type="button" className="button button-quiet" disabled={form.blocked} onClick={() => form.saving.mutate(null)}>প্রোফাইলের ছবি সরান</button>}
      {form.saving.error && <button type="button" className="button button-quiet" onClick={reloadManagedForm}>বর্তমান ছবি ও তথ্য খুলুন</button>}
    </div></form>;
}
