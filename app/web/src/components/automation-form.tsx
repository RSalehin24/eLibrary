"use client";

import { SiteFieldErrors } from "./site-field-errors";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createAutomation, updateAutomation } from "@/api/automations";
import type { AutomationCreate, SourceAutomation } from "@/api/types";
import { automationFrequencies } from "@/lib/automation-status";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountField } from "./account-field";
import { AccountFeedback } from "./account-feedback";
import { useAdminLanguage } from "./admin-language";

export function AutomationForm({ automation, onSaved }: { automation?: SourceAutomation; onSaved?: () => void }) {
  const { t } = useAdminLanguage();
  const router = useRouter(), client = useQueryClient();
  const [identifier, setIdentifier] = useState(automation?.id ?? "");
  const [scope, setScope] = useState(automation ? automation.fetch_all ? "all" : "limited" : "all");
  const [action, setAction] = useState(automation ? automation.process_all ? "all" : automation.processing_limit ? "limited" : "fetch" : "all");
  const revision = useRef(automation?.updated_at ?? "");
  const form = useManagedForm(async (values: AutomationCreate) => {
    if (!automation) return createAutomation(values);
    const { operation_id: operationId, ...fields } = values;
    return updateAutomation(operationId, { ...fields, expected_updated_at: revision.current });
  }, async (saved) => { revision.current = saved.updated_at; await client.invalidateQueries({ queryKey: ["private", "automations"] }); if (onSaved) onSaved(); else if (!automation) router.push(`/manage/automations/${saved.id}/`); router.refresh(); });
  return <form className="account-section automation-form" onChange={form.markDirty} onReset={() => { form.discard(); setScope(automation?.fetch_all ? "all" : automation ? "limited" : "all"); setAction(automation?.process_all ? "all" : automation ? automation.processing_limit ? "limited" : "fetch" : "all"); }} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    const operationId = identifier || crypto.randomUUID(); setIdentifier(operationId);
    form.saving.mutate({ operation_id: operationId, name: String(fields.get("name")), enabled: fields.has("enabled"), frequency: String(fields.get("frequency")) as AutomationCreate["frequency"],
      first_run_local: `${fields.get("first_run_date")}T${fields.get("first_run_time")}`, time_zone: String(fields.get("time_zone")), fetch_all: scope === "all", process_all: action === "all",
      source_max_pages: scope === "all" ? 20 : Number(fields.get("source_max_pages")), processing_limit: action === "limited" ? Number(fields.get("processing_limit")) : 0 });
  }}><div className="automation-form-grid">
    <AccountField name="name" label="সময়সূচির নাম" initial={automation?.name} required maxLength={150} errors={form.errors.name} disabled={form.blocked} />
    <div className="form-field"><label htmlFor="frequency">{t("কত দিন পরপর চলবে")}</label><select id="frequency" name="frequency" defaultValue={automation?.frequency ?? "daily"} disabled={form.blocked}>{Object.entries(automationFrequencies).map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select></div>
    <div className="form-field"><label htmlFor="first_run_date">{t("প্রথম তারিখ")}</label><input id="first_run_date" name="first_run_date" type="date" required defaultValue={automation?.first_run_local.split("T")[0]} disabled={form.blocked} aria-invalid={!!form.errors.first_run_local?.length} /></div>
    <div className="form-field"><label htmlFor="first_run_time">{t("সময়")}</label><input id="first_run_time" name="first_run_time" type="time" required defaultValue={automation?.first_run_local.split("T")[1] ?? "02:00"} disabled={form.blocked} aria-invalid={!!form.errors.first_run_local?.length} /></div>
    <AccountField name="time_zone" label="সময়ের অঞ্চল" initial={automation?.time_zone ?? "Asia/Dhaka"} required maxLength={64} errors={form.errors.time_zone} disabled={form.blocked} />
    <div className="form-field"><label htmlFor="catalog-scope">{t("সংগ্রহের পরিমাণ")}</label><select id="catalog-scope" value={scope} onChange={(event) => setScope(event.target.value)} disabled={form.blocked}><option value="all">{t("সব পাতা সংগ্রহ")}</option><option value="limited">{t("পাতার সীমা নির্ধারণ")}</option></select></div>
    {scope === "limited" && <AccountField name="source_max_pages" label="একবারে উৎসের সর্বোচ্চ পাতা" type="number" initial={String(automation?.source_max_pages ?? 20)} required min={1} max={200} disabled={form.blocked} errors={form.errors.source_max_pages} />}
    <div className="form-field"><label htmlFor="scheduled-action">{t("কী কাজ চলবে")}</label><select id="scheduled-action" value={action} onChange={(event) => setAction(event.target.value)} disabled={form.blocked}><option value="all">{t("সব যোগ্য বই তৈরি")}</option><option value="limited">{t("নির্দিষ্ট সংখ্যক বই তৈরি")}</option><option value="fetch">{t("শুধু তালিকা সংগ্রহ")}</option></select></div>
    {action === "limited" && <AccountField name="processing_limit" label="সংগৃহীত উৎস থেকে সর্বোচ্চ কতটি বই প্রস্তুত হবে" type="number" initial={String(automation?.processing_limit || 10)} required min={1} max={100} disabled={form.blocked} errors={form.errors.processing_limit} />}
  </div>
    <p className="muted">{t("নতুন বা পরিবর্তিত সময় ভবিষ্যতের হতে হবে। মাসের শেষ দিনের সময়সূচি ছোট মাসে শেষ দিনে চলবে।")}</p>{form.errors.first_run_local && <p className="field-error" role="alert"><SiteFieldErrors errors={form.errors.first_run_local} /></p>}
    <label className="checkbox-field"><input name="enabled" type="checkbox" defaultChecked={automation?.enabled ?? false} disabled={form.blocked} />{t("সময়সূচি সক্রিয়")}</label>
    <AccountFeedback error={form.saving.error} /><div className="account-actions"><button className="button" disabled={form.blocked}>{t("সময়সূচি সংরক্ষণ করুন")}</button>{form.dirty && !form.saving.error && <button className="button button-quiet" type="reset" disabled={form.saving.isPending}>{t("লেখা বাদ দিন")}</button>}{form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}>{t("বর্তমান তথ্য খুলুন")}</button>}</div>
    {form.saving.isSuccess && <p role="status">{t("সময়সূচি সংরক্ষিত হয়েছে।")}</p>}
    {form.saving.error && identifier && <Link className="text-link" href={`/manage/automations/${identifier}/`}>{t("এই সময়সূচির বর্তমান অবস্থা দেখুন →")}</Link>}
  </form>;
}
