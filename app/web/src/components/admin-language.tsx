"use client";

import { translateAdmin, type AdminLanguage } from "@/lib/admin-language";
import { jobTimestamp } from "@/lib/job-status";
import { SiteLanguageSwitch, useSiteLanguage } from "./site-language";

export function AdminLanguageProvider({ children }: { initial: AdminLanguage; children: React.ReactNode }) {
  return <div className="management-workspace" lang={useSiteLanguage().language}>{children}</div>;
}

export function AdminLanguageSwitch() {
  return <SiteLanguageSwitch />;
}

export function useAdminLanguage() {
  const { language, number } = useSiteLanguage();
  return { language, t: (text: string) => translateAdmin(language, text),
    number };
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

export function AdminNavigation({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return <nav className={className} aria-label={useAdminLanguage().t(label)}>{children}</nav>;
}
