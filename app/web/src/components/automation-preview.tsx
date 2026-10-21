"use client";

import { automationFrequencies } from "@/lib/automation-status";
import { useAdminLanguage } from "./admin-language";

type Preview = Readonly<Record<string, string>>;

export function AutomationPreview({ values, action }: { values: Preview; action: string }) {
  const { t, language } = useAdminLanguage();
  const date = new Date(`${values.first_run_date}T${(values.first_run_time || "02:00").slice(0, 5)}:00Z`);
  const firstRun = Number.isNaN(date.getTime()) ? t("প্রথম তারিখ বেছে নিন") : new Intl.DateTimeFormat(language, { timeZone: "UTC", day: "numeric", month: "long", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true }).format(date);
  return <section className="automation-preview" aria-label={t("সময়সূচির সারাংশ")}><h2>{t("সময়সূচির সারাংশ")}</h2><dl>
    <div><dt>{t("কী কাজ চলবে")}</dt><dd>{t(action === "all" ? "সব যোগ্য বই তৈরি" : action === "limited" ? "নির্দিষ্ট সংখ্যক বই তৈরি" : "শুধু তালিকা সংগ্রহ")}</dd></div>
    <div><dt>{t("কোন বই পরীক্ষা হবে")}</dt><dd>{t(values.catalog_scope === "unfinished" ? "অসম্পূর্ণ বই" : "সব বই")}</dd></div>
    <div><dt>{t("কত দিন পরপর চলবে")}</dt><dd>{t(automationFrequencies[values.frequency as keyof typeof automationFrequencies] ?? "প্রতিদিন")}</dd></div>
    <div><dt>{t("প্রথমবার চলবে")}</dt><dd>{firstRun} · {values.time_zone === "Asia/Dhaka" ? t("ঢাকা") : values.time_zone}</dd></div>
  </dl><p>{t(action === "fetch" ? "শুধু ওয়েবসাইটের বইয়ের তালিকা হালনাগাদ হবে।" : "স্বয়ংক্রিয়ভাবে যাচাই ও প্রকাশ করা হবে।")}</p></section>;
}
