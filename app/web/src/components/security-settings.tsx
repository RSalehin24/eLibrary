"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { readSecurity } from "@/api/account";
import type { AccountProfile, TOTPSetup } from "@/api/types";
import { SecurityConfirmation } from "./security-confirmation";
import { DisableSecurityForm, StartSecurityForm } from "./security-forms";

export function SecuritySettings({ profile, nextPath, onChanged }: { profile: AccountProfile; nextPath: string; onChanged: () => Promise<void> }) {
  const client = useQueryClient();
  const [setup, setSetup] = useState<TOTPSetup | null>(null);
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState("");
  const security = useQuery({ queryKey: ["private", "security"], queryFn: ({ signal }) => readSecurity(signal), refetchOnWindowFocus: false });
  async function changed(message: string) {
    setSetup(null); setEditing(false); setNotice(message);
    await Promise.all([client.invalidateQueries({ queryKey: ["private", "security"] }), onChanged()]);
  }
  const status = security.data;
  let securityForm = null;
  if (setup) securityForm = <SecurityConfirmation setup={setup} onConfirmed={() => changed("দুই ধাপের নিরাপত্তা চালু হয়েছে।")} onCancelled={() => changed("অসম্পূর্ণ সেটআপ বাতিল হয়েছে।")} />;
  else if (editing && status?.enabled) securityForm = <DisableSecurityForm onDisabled={() => changed("দুই ধাপের নিরাপত্তা বন্ধ হয়েছে।")} onCancel={() => setEditing(false)} />;
  else if (editing) securityForm = <StartSecurityForm onStarted={setSetup} onCancel={() => setEditing(false)} />;
  else if (status && (!status.enabled || !status.required)) securityForm = <button className="button button-quiet" onClick={() => setEditing(true)}>{status.enabled ? "নিরাপত্তা বন্ধ করার সেটিংস" : "দুই ধাপের নিরাপত্তা চালু করুন"}</button>;
  return <section className="account-section" aria-labelledby="security-heading"><h2 id="security-heading">দুই ধাপের নিরাপত্তা</h2>
    {notice && <p role="status">{notice}</p>}
    {security.error && <p className="field-error" role="alert">নিরাপত্তার অবস্থা পাওয়া যায়নি। <button className="button button-quiet" onClick={() => void security.refetch()}>আবার দেখুন</button></p>}
    {!status && !security.error && <p role="status">নিরাপত্তার অবস্থা দেখা হচ্ছে…</p>}
    {status?.setup_required && <p className="notice">এই অ্যাকাউন্টে দুই ধাপের নিরাপত্তা চালু করতে হবে। তারপর পাঠাগারে ফিরতে পারবেন।</p>}
    {status?.enabled && <p>দুই ধাপের নিরাপত্তা চালু আছে। প্রবেশের সময় পাসওয়ার্ডের সঙ্গে অ্যাপের কোড লাগবে।</p>}
    {status?.required && status.enabled && <p className="muted">অ্যাকাউন্টের নিয়ম অনুযায়ী এটি চালু রাখতে হবে।</p>}
    {status?.pending_setup && !setup && <p>আগের সেটআপটি অসম্পূর্ণ আছে। পাসওয়ার্ড দিয়ে সেটি আবার খুলতে পারবেন।</p>}
    {securityForm}
    {status?.enabled && profile.totp_required && <p><Link className="text-link" href={nextPath}>পাঠাগারে ফিরে যান</Link></p>}
  </section>;
}
