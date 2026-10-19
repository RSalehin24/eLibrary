"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { jobKinds, jobStates } from "@/lib/job-status";
import { jobCoverageLabels, jobFilterQuery, jobLayoutLabels, savedQueueFilter } from "@/lib/job-filters";
import { AdminText, useAdminLanguage } from "./admin-language";
import { Icon } from "./icon";
import { SavedFilterControls } from "./saved-filter-controls";

const selectFilters = [
  { key: "state", label: "কাজের অবস্থা", all: "সব অবস্থা", choices: jobStates },
  { key: "kind", label: "কাজের ধরন", all: "সব ধরনের কাজ", choices: Object.fromEntries(Object.entries(jobKinds).filter(([kind]) => kind !== "account_mail")) },
  { key: "coverage", label: "লেখার যাচাই", all: "সব যাচাইয়ের অবস্থা", choices: jobCoverageLabels },
  { key: "layout", label: "সূচিপত্র ও লেখার ধরন", all: "সব ধরনের সূচিপত্র ও লেখা", choices: jobLayoutLabels },
];

export function JobFiltersForm({ filter }: { filter: string }) {
  const { t } = useAdminLanguage(), id = useId();
  const [values, setValues] = useState(Object.fromEntries(new URLSearchParams(filter)));
  const update = (key: string, value: string) => setValues({ ...values, [key]: value });
  return <><form className="catalog-filters-form" action="/manage/jobs/" role="search">
    {["view", "book", "parent_job", "automation_run"].map((key) => values[key] && <input key={key} name={key} value={values[key]} type="hidden" />)}
    <div className="search-form"><label className="visually-hidden" htmlFor={`${id}-search`}><AdminText>{"কাজ খুঁজুন"}</AdminText></label><input id={`${id}-search`} name="q" type="search" value={values.q ?? ""} maxLength={120} placeholder={t("বইয়ের নাম, কাজের আইডি বা সমস্যার কোড")} onChange={(event) => update("q", event.target.value)} /><button className="button"><Icon name="search" /><AdminText>{"খুঁজুন"}</AdminText></button></div>
    <div className="catalog-filter-grid">
      {selectFilters.map(({ key, label, all, choices }) => <div className="catalog-filter-field" key={key}><label htmlFor={`${id}-${key}`}>{t(label)}</label><select id={`${id}-${key}`} name={key} value={values[key] ?? ""} onChange={(event) => update(key, event.target.value)}><option value="">{t(all)}</option>{Object.entries(choices).map(([value, text]) => <option key={value} value={value}>{t(text)}</option>)}</select></div>)}
      <div className="catalog-filter-field"><label htmlFor={`${id}-error`}><AdminText>{"সমস্যার কোড"}</AdminText></label><input id={`${id}-error`} name="error_code" value={values.error_code ?? ""} maxLength={64} pattern="[a-z][a-z0-9_]{0,63}" onChange={(event) => update("error_code", event.target.value)} /></div>
    </div>
    <div className="account-actions"><button className="button button-quiet"><Icon name="settings" /><AdminText>{"ফিল্টার প্রয়োগ করুন"}</AdminText></button><Link className="text-link" href="/manage/jobs/"><Icon name="refresh" /><AdminText>{"সব ফিল্টার মুছুন"}</AdminText></Link></div>
  </form><SavedFilterControls target="queue" values={Object.fromEntries(Object.entries(values).filter(([key, value]) => key !== "page" && !!value))} href={(parameters) => { const conditions = savedQueueFilter(parameters); return conditions ? `/manage/jobs/?${jobFilterQuery(conditions)}` : null; }} /></>;
}
