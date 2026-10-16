"use client";

import { createContext, useContext, useState } from "react";
import { adminLanguageCookie, translateAdmin, type AdminLanguage } from "@/lib/admin-language";
import { jobTimestamp } from "@/lib/job-status";

const LanguageContext = createContext<AdminLanguage>("bn");

export function AdminLanguageProvider({ initial, children }: { initial: AdminLanguage; children: React.ReactNode }) {
  const [language, setLanguage] = useState(initial);
  function changeLanguage(next: AdminLanguage) {
    document.cookie = `${adminLanguageCookie}=${next}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`;
    setLanguage(next);
  }
  return <LanguageContext.Provider value={language}><div className="management-workspace" lang={language}>
    <div className="admin-language" role="group" aria-label="Language / ভাষা">
      <button type="button" lang="bn" aria-pressed={language === "bn"} onClick={() => changeLanguage("bn")}>বাংলা</button>
      <button type="button" lang="en" aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>English</button>
    </div>{children}</div></LanguageContext.Provider>;
}

export function useAdminLanguage() {
  const language = useContext(LanguageContext);
  return { language, t: (text: string) => translateAdmin(language, text),
    number: (value: number) => new Intl.NumberFormat(language).format(value) };
}

export function AdminText({ children }: { children: string }) {
  return useAdminLanguage().t(children);
}

export function AdminNumber({ value }: { value: number }) {
  return useAdminLanguage().number(value);
}

export function AdminDate({ value }: { value: string | null }) {
  return jobTimestamp(value, useAdminLanguage().language);
}
