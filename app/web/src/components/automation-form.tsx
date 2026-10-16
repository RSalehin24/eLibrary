"use client";

import { AdminText } from "@/components/admin-language";
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

export function AutomationForm({ automation }: { automation?: SourceAutomation }) {
  const router = useRouter();
  const client = useQueryClient();
  const [identifier, setIdentifier] = useState(automation?.id ?? "");
  const revision = useRef(automation?.updated_at ?? "");
  const form = useManagedForm(async (values: AutomationCreate) => {
    if (automation) {
      const { operation_id: operationId, ...fields } = values;
      return updateAutomation(operationId, { ...fields, expected_updated_at: revision.current });
    }
    return createAutomation(values);
  }, async (saved) => { revision.current = saved.updated_at; await client.invalidateQueries({ queryKey: ["private", "automations"] }); if (!automation) router.push(`/manage/automations/${saved.id}/`); router.refresh(); });
  return <form className="account-section" onChange={form.markDirty} onReset={form.discard} onSubmit={(event) => {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    const operationId = identifier || crypto.randomUUID(); setIdentifier(operationId);
    const frequency = String(fields.get("frequency")) as AutomationCreate["frequency"];
    form.saving.mutate({ operation_id: operationId, name: String(fields.get("name")), enabled: fields.has("enabled"), frequency,
      first_run_local: `${fields.get("first_run_date")}T${fields.get("first_run_time")}`, time_zone: String(fields.get("time_zone")),
      source_max_pages: Number(fields.get("source_max_pages")), processing_limit: Number(fields.get("processing_limit")) });
  }}><h2><AdminText>{"সময়সূচির তথ্য"}</AdminText></h2>
    <AccountField name="name" label="সময়সূচির নাম" initial={automation?.name} required maxLength={150} errors={form.errors.name} disabled={form.blocked} />
    <div className="form-field"><label htmlFor="frequency"><AdminText>{"কত দিন পরপর চলবে"}</AdminText></label><select id="frequency" name="frequency" defaultValue={automation?.frequency ?? "daily"} disabled={form.blocked}>{Object.entries(automationFrequencies).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}</select></div>
    <div className="form-field"><label htmlFor="first_run_date"><AdminText>{"প্রথমবার চলার স্থানীয় তারিখ"}</AdminText></label><input id="first_run_date" name="first_run_date" type="date" required defaultValue={automation?.first_run_local.split("T")[0]} disabled={form.blocked} aria-invalid={!!form.errors.first_run_local?.length} aria-describedby="first-run-help" /></div>
    <div className="form-field"><label htmlFor="first_run_time"><AdminText>{"প্রথমবার চলার স্থানীয় সময়"}</AdminText></label><input id="first_run_time" name="first_run_time" type="time" required defaultValue={automation?.first_run_local.split("T")[1]} disabled={form.blocked} aria-invalid={!!form.errors.first_run_local?.length} aria-describedby="first-run-help" /><p className="muted" id="first-run-help"><AdminText>{"নতুন বা পরিবর্তিত সময় ভবিষ্যতের হতে হবে। মাসের শেষ দিনের সময়সূচি ছোট মাসে শেষ দিনে চলবে।"}</AdminText></p>{form.errors.first_run_local && <p className="field-error">{form.errors.first_run_local.join(" ")}</p>}</div>
    <AccountField name="time_zone" label="সময়ের অঞ্চল (যেমন Asia/Dhaka)" initial={automation?.time_zone ?? "Asia/Dhaka"} required maxLength={64} errors={form.errors.time_zone} disabled={form.blocked} />
    <div className="form-field"><label htmlFor="source_max_pages"><AdminText>{"একবারে উৎসের সর্বোচ্চ পাতা"}</AdminText></label><input id="source_max_pages" name="source_max_pages" type="number" required min="1" max="200" defaultValue={automation?.source_max_pages ?? 20} disabled={form.blocked} /></div>
    <div className="form-field"><label htmlFor="processing_limit"><AdminText>{"সংগৃহীত উৎস থেকে সর্বোচ্চ কতটি বই প্রস্তুত হবে"}</AdminText></label><input id="processing_limit" name="processing_limit" type="number" required min="0" max="100" defaultValue={automation?.processing_limit ?? 0} disabled={form.blocked} /><p className="muted"><AdminText>{"০ রাখলে শুধু উৎসের পরিচিতি সংগ্রহ হবে। প্রস্তুত বই সম্পাদকের পর্যালোচনার অপেক্ষায় থাকবে।"}</AdminText></p></div>
    <label className="checkbox-field"><input name="enabled" type="checkbox" defaultChecked={automation?.enabled ?? false} disabled={form.blocked} /><AdminText>{"সময়সূচি সক্রিয়"}</AdminText></label>
    <p className="muted"><AdminText>{"সংরক্ষণকারী পরিচালকের বর্তমান অনুমতিতে কাজ চলবে। বন্ধ করলে পরের নির্ধারিত কাজ শুরু হবে না। ইতিমধ্যে শুরু হওয়া কাজের নিয়ন্ত্রণ কাজের পাতায় আছে।"}</AdminText></p>
    <AccountFeedback error={form.saving.error} /><div className="account-actions"><button className="button" disabled={form.blocked}><AdminText>{"সময়সূচি সংরক্ষণ করুন"}</AdminText></button>{form.dirty && !form.saving.error && <button className="button button-quiet" type="reset" disabled={form.saving.isPending}><AdminText>{"লেখা বাদ দিন"}</AdminText></button>}{form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}><AdminText>{"বর্তমান তথ্য খুলুন"}</AdminText></button>}</div>
    {form.saving.isSuccess && <p role="status"><AdminText>{"সময়সূচি সংরক্ষিত হয়েছে।"}</AdminText></p>}
    {form.saving.error && identifier && <p><Link className="text-link" href={`/manage/automations/${identifier}/`}><AdminText>{"এই সময়সূচির বর্তমান অবস্থা দেখুন →"}</AdminText></Link></p>}
  </form>;
}
