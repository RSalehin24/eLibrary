"use client";

import { SiteText } from "@/components/site-language";

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
  return <div className="account-settings">{notice && <p role="status"><SiteText>{notice}</SiteText></p>}
    {profileQuery.error && <p className="field-error" role="alert"><SiteText>{"বর্তমান প্রোফাইল পাওয়া যায়নি। আবার তথ্য দেখুন।"}</SiteText></p>}
    <nav className="account-section-nav"><a href="#profile-identity"><SiteText>আপনার পরিচয়</SiteText></a><a href="#profile-security"><SiteText>দুই ধাপের নিরাপত্তা</SiteText></a><a href="#profile-password"><SiteText>পাসওয়ার্ড বদলান</SiteText></a>{profile.can_configure_kindle && <a href="#profile-kindle"><SiteText>কিন্ডলের ঠিকানা</SiteText></a>}</nav>
    <div className="profile-section-grid" id="profile-identity"><ProfileIdentityForm profile={profile} onSaved={onSaved} /><ProfileImageForm profile={profile} onSaved={onSaved} /></div>
    <div id="profile-security"><SecuritySettings profile={profile} nextPath={nextPath} onChanged={refreshSecurity} /></div>
    <div id="profile-password"><ProfilePasswordForm profile={profile} onSaved={onSaved} /></div>
    {profile.can_configure_kindle && <div id="profile-kindle"><ProfileKindleForm profile={profile} onSaved={onSaved} /></div>}
    <div className="account-actions"><button className="button button-quiet" onClick={() => window.location.reload()}><SiteText>বর্তমান তথ্য দেখুন</SiteText></button></div>
  </div>;
}
