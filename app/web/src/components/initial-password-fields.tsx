"use client";

import { useState } from "react";
import { generateInitialPassword } from "@/lib/initial-password";
import { useAdminLanguage } from "./admin-language";
import { SiteFieldErrors } from "./site-field-errors";
import "./initial-password-fields.css";

export function InitialPasswordFields({ disabled, errors }: { disabled: boolean; errors: Record<string, string[]> }) {
  const { t } = useAdminLanguage();
  const [password, setPassword] = useState(""), [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false), [copyStatus, setCopyStatus] = useState("");
  function generate() { const value = generateInitialPassword(); setPassword(value); setConfirmation(value); setCopyStatus(""); }
  async function copy() {
    try { await navigator.clipboard.writeText(password); setCopyStatus("পাসওয়ার্ড কপি হয়েছে।"); }
    catch { setCopyStatus("পাসওয়ার্ড কপি করা যায়নি। লেখাটি নির্বাচন করে কপি করুন।"); }
  }
  return <fieldset className="initial-password-fields" disabled={disabled}>
    <legend>{t("প্রথমবার প্রবেশের পাসওয়ার্ড")}</legend><p className="muted">{t("অন্তত ১২ অক্ষর দিন। পাঠকের সঙ্গে নিরাপদে পাসওয়ার্ড শেয়ার করুন। ইমেইল পাঠানো হবে না।")}</p>
    <div className="form-field"><label htmlFor="initial-password">{t("প্রাথমিক পাসওয়ার্ড")}</label><input id="initial-password" name="password" type={visible ? "text" : "password"} value={password} onChange={(event) => { setPassword(event.target.value); setCopyStatus(""); }} required minLength={12} maxLength={4096} autoComplete="new-password" aria-invalid={!!errors.password?.length} aria-describedby={errors.password?.length ? "initial-password-error" : undefined} />
      {!!errors.password?.length && <p id="initial-password-error" className="field-error"><SiteFieldErrors errors={errors.password} /></p>}</div>
    <div className="form-field"><label htmlFor="confirm-password">{t("প্রাথমিক পাসওয়ার্ড আবার লিখুন")}</label><input id="confirm-password" name="confirm_password" type={visible ? "text" : "password"} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required minLength={12} maxLength={4096} autoComplete="new-password" aria-invalid={!!errors.confirm_password?.length} aria-describedby={errors.confirm_password?.length ? "confirm-password-error" : undefined} />
      {!!errors.confirm_password?.length && <p id="confirm-password-error" className="field-error"><SiteFieldErrors errors={errors.confirm_password} /></p>}</div>
    <div className="account-actions"><button className="button button-quiet" type="button" onClick={generate}>{t("নিরাপদ পাসওয়ার্ড তৈরি করুন")}</button><button className="button button-quiet" type="button" onClick={() => setVisible((value) => !value)} aria-pressed={visible}>{t(visible ? "পাসওয়ার্ড আড়াল করুন" : "পাসওয়ার্ড দেখুন")}</button><button className="button button-quiet" type="button" disabled={!password} onClick={() => void copy()}>{t("পাসওয়ার্ড কপি করুন")}</button></div>
    {copyStatus && <p role="status">{t(copyStatus)}</p>}
  </fieldset>;
}
