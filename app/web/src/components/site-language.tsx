"use client";

import { createContext, useContext, useEffect, useSyncExternalStore, type ReactNode, type ComponentProps } from "react";
import Link from "next/link";
import Image from "next/image";
import { announceSiteLanguage, browserLanguage, subscribeSiteLanguage, translateSite, updateDocumentLanguage } from "@/lib/site-language";
import type { AdminLanguage } from "@/lib/admin-language";
import { jobTimestamp } from "@/lib/job-status";

const SiteLanguageContext = createContext<{ language: AdminLanguage; changeLanguage: (next: AdminLanguage) => void }>({ language: "bn", changeLanguage: () => {} });

export function SiteLanguageProvider({ initial, children }: { initial: AdminLanguage; children: ReactNode }) {
  const language = useSyncExternalStore(subscribeSiteLanguage, browserLanguage, () => initial);
  useEffect(() => {
    const update = () => updateDocumentLanguage(language);
    update();
    // Route metadata may arrive after the static shell hydrates.
    const observer = new MutationObserver(update);
    observer.observe(document.head, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, [language]);
  function changeLanguage(next: AdminLanguage) {
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `library-language=${next}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
    document.cookie = `library-admin-language=${next}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
    announceSiteLanguage();
  }
  return <SiteLanguageContext.Provider value={{ language, changeLanguage }}>{children}</SiteLanguageContext.Provider>;
}

export function useSiteLanguage() {
  const context = useContext(SiteLanguageContext);
  return { ...context, t: (text: string) => translateSite(context.language, text), number: (value: number) => new Intl.NumberFormat(context.language, { numberingSystem: context.language === "bn" ? "beng" : "latn" }).format(value) };
}

export function SiteText({ children }: { children: ReactNode }) {
  const { t } = useSiteLanguage();
  return typeof children === "string" ? t(children) : children;
}

export function SiteNumber({ value }: { value: number }) { return useSiteLanguage().number(value); }
export function SiteDate({ value }: { value: string | null }) { return jobTimestamp(value, useSiteLanguage().language); }
export function SiteDiv(props: ComponentProps<"div">) { return <div {...useSiteAttributes(props)} />; }
export function SiteSection(props: ComponentProps<"section">) { return <section {...useSiteAttributes(props)} />; }

export function SiteLanguageSwitch() {
  const { language, changeLanguage } = useSiteLanguage();
  return <SiteDiv className="admin-language" role="group" aria-label="Language / ভাষা">
    <button type="button" lang="bn" aria-pressed={language === "bn"} onClick={() => changeLanguage("bn")}>বাংলা</button>
    <button type="button" lang="en" aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>English</button>
  </SiteDiv>;
}

function useSiteAttributes<T extends { "aria-label"?: string; title?: string; placeholder?: string; alt?: string }>(props: T) {
  const { t } = useSiteLanguage();
  return { ...props, ...(props["aria-label"] ? { "aria-label": t(props["aria-label"]) } : {}), ...(props.title ? { title: t(props.title) } : {}), ...(props.placeholder ? { placeholder: t(props.placeholder) } : {}), ...(props.alt ? { alt: t(props.alt) } : {}) };
}

export function SiteNav(props: ComponentProps<"nav">) { return <nav {...useSiteAttributes(props)} />; }
export function SiteSelect(props: ComponentProps<"select">) { return <select {...useSiteAttributes(props)} />; }
export function SiteInput(props: ComponentProps<"input">) { return <input {...useSiteAttributes(props)} />; }
export function SiteButton(props: ComponentProps<"button">) { return <button {...useSiteAttributes(props)} />; }
export function SiteTextarea(props: ComponentProps<"textarea">) { return <textarea {...useSiteAttributes(props)} />; }
export function SiteForm(props: ComponentProps<"form">) { return <form {...useSiteAttributes(props)} />; }
export function SiteNextImage(props: ComponentProps<typeof Image>) { const attributes = useSiteAttributes(props); return <Image {...attributes} alt={attributes.alt} />; }
export function SiteLink(props: ComponentProps<typeof Link>) { return <Link {...useSiteAttributes(props)} />; }
export function SiteAnchor(props: ComponentProps<"a">) { return <a {...useSiteAttributes(props)} />; }
