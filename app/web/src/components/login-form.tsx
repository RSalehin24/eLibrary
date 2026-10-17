"use client";

import { SiteText } from "@/components/site-language";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { signIn } from "@/api/auth";
import { APIError } from "@/api/http";
import { returnPath } from "@/lib/return-path";
import Link from "next/link";

function loginErrorMessage(error: Error) {
  if (!(error instanceof APIError)) return "প্রবেশ করা যায়নি। সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।";
  if (error.code === "otp_required") return "দুই ধাপের নিরাপত্তা চালু আছে। অথেনটিকেটর অ্যাপের কোড দিন।";
  if (error.code === "otp_invalid") return "নিরাপত্তা কোডটি সঠিক নয়। নতুন কোড দিয়ে আবার চেষ্টা করুন।";
  if (error.status === 429) return "অনেকবার চেষ্টা করা হয়েছে। কিছুক্ষণ পরে আবার চেষ্টা করুন।";
  if (error.status >= 500) return "প্রবেশ করা যায়নি। কিছুক্ষণ পরে আবার চেষ্টা করুন।";
  return "ইমেইল ও পাসওয়ার্ড পরীক্ষা করে আবার চেষ্টা করুন।";
}

export function LoginForm({ nextPath }: { nextPath: string }) {
  const client = useQueryClient();
  const [codeRequired, setCodeRequired] = useState(false);
  const codeInput = useRef<HTMLInputElement>(null);
  const login = useMutation({ mutationFn: signIn, onSuccess: () => {
    client.clear(); window.location.replace(returnPath(nextPath));
  }, onError: (error) => {
    if (error instanceof APIError && ["otp_required", "otp_invalid"].includes(error.code)) setCodeRequired(true);
  } });
  useEffect(() => { if (codeRequired) codeInput.current?.focus(); }, [codeRequired]);
  function changeCredentials() { setCodeRequired(false); login.reset(); }
  const codeRequested = login.error instanceof APIError && login.error.code === "otp_required";
  return <form className="account-form" onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    login.mutate({ email: String(fields.get("email")), password: String(fields.get("password")),
      otp_token: String(fields.get("otp_token") || "") });
  }}><p className="eyebrow"><SiteText>{"আপনার ব্যক্তিগত পাঠাগার"}</SiteText></p><h1><SiteText>{"অ্যাকাউন্টে প্রবেশ করুন"}</SiteText></h1>
    <p className="login-description"><SiteText>{"আপনার বই, বুকমার্ক আর নোটের কাছে ফিরে যান।"}</SiteText></p>
    <div className="form-field"><label htmlFor="email"><SiteText>{"ইমেইল"}</SiteText></label><input id="email" name="email" type="email" autoComplete="username" onChange={changeCredentials} disabled={login.isPending} required /></div>
    <div className="form-field"><label htmlFor="password"><SiteText>{"পাসওয়ার্ড"}</SiteText></label><input id="password" name="password" type="password" autoComplete="current-password" maxLength={4096} onChange={changeCredentials} disabled={login.isPending} required /></div>
    {codeRequired && <div className="form-field"><label htmlFor="otp"><SiteText>{"দুই ধাপের নিরাপত্তা কোড"}</SiteText></label><input ref={codeInput} id="otp" name="otp_token" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}([0-9]{2})?" maxLength={8} disabled={login.isPending} required aria-describedby="otp-help" />
      <p id="otp-help" className="muted"><SiteText>{"আপনার অথেনটিকেটর অ্যাপের বর্তমান কোড দিন।"}</SiteText></p></div>}
    {login.error && <p className={codeRequested ? "login-challenge" : "field-error"} role="alert"><SiteText>{loginErrorMessage(login.error)}</SiteText></p>}
    <button className="button" type="submit" disabled={login.isPending}>{login.isPending ? <SiteText>{"প্রবেশ করা হচ্ছে…"}</SiteText> : <SiteText>{"প্রবেশ করুন"}</SiteText>}</button>
    <Link className="text-link" href="/reset-password/"><SiteText>{"পাসওয়ার্ড ভুলে গেছেন?"}</SiteText></Link>
  </form>;
}
