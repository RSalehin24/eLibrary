"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { readProfile } from "@/api/account";
import type { AccountProfile } from "@/api/types";
import { ProfileIdentityForm, ProfileKindleForm, ProfilePasswordForm } from "./profile-forms";
import { SecuritySettings } from "./security-settings";
import { ProfileImageForm } from "./profile-image-form";

export function AccountSettings({ initialProfile, nextPath }: { initialProfile: AccountProfile; nextPath: string }) {
  const client = useQueryClient();
  const router = useRouter();
  const [notice, setNotice] = useState("");
  const profileQuery = useQuery({ queryKey: ["private", "profile"], queryFn: ({ signal }) => readProfile(signal), initialData: initialProfile, refetchOnWindowFocus: false });
  const profile = profileQuery.data;
  async function onSaved(updated: AccountProfile) {
    client.setQueryData(["private", "profile"], updated); setNotice("পরিবর্তন সংরক্ষিত হয়েছে।");
    await Promise.all([client.invalidateQueries({ queryKey: ["private", "session"] }), client.invalidateQueries({ queryKey: ["private", "kindle"] })]); router.refresh();
  }
  async function refreshSecurity() {
    await Promise.all([client.invalidateQueries({ queryKey: ["private", "session"] }), client.invalidateQueries({ queryKey: ["private", "profile"] })]);
    router.refresh();
  }
  return <div className="account-settings">{notice && <p role="status">{notice}</p>}
    {profileQuery.error && <p className="field-error" role="alert">বর্তমান প্রোফাইল পাওয়া যায়নি। আবার তথ্য দেখুন।</p>}
    <div className="account-actions"><button className="button button-quiet" onClick={() => window.location.reload()}>বর্তমান তথ্য দেখুন</button><p className="muted">নতুন তথ্য খুললে সংরক্ষণ না করা ফর্ম আবার লিখতে হতে পারে।</p></div>
    <ProfileIdentityForm profile={profile} onSaved={onSaved} />
    <ProfileImageForm profile={profile} onSaved={onSaved} />
    <SecuritySettings profile={profile} nextPath={nextPath} onChanged={refreshSecurity} />
    <ProfilePasswordForm profile={profile} onSaved={onSaved} />
    {profile.can_configure_kindle && <ProfileKindleForm profile={profile} onSaved={onSaved} />}
  </div>;
}
