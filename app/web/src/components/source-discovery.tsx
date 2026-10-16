"use client";

import Link from "next/link";
import { useState } from "react";
import { discoverSources } from "@/api/source-processing";
import type { SourceDiscoveryCommand, SourceDiscoveryOptions } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { useAdminLanguage } from "./admin-language";

export function SourceDiscovery({ options }: { options: SourceDiscoveryOptions }) {
  const { t } = useAdminLanguage();
  const [identifier, setIdentifier] = useState<string | null>(null);
  const form = useManagedForm((values: SourceDiscoveryCommand) => discoverSources(values), async () => {});
  const revision = options.configuration_revision;
  if (!options.configured || !revision) return <section className="source-sync"><h2>{t("নতুন উৎস আবিষ্কার")}</h2><p className="notice">{t("বইয়ের তালিকা সংগ্রহ করতে ওয়েবসাইটের সেটিংস ঠিক করতে হবে।")}</p></section>;
  return <section className="source-sync"><div><h2>{t("নতুন উৎস আবিষ্কার")}</h2><p>{t("উৎসের তালিকা থেকে বইয়ের নাম ও লেখকের তথ্য আনা হবে।")}</p><p className="muted source-website">{t("ওয়েবসাইট")}: {options.catalog_url}</p></div>
    {options.active_operation_id ? <Link className="text-link" href={`/manage/jobs/${options.active_operation_id}/`}>{t("চলমান সিঙ্ক দেখুন")} →</Link> : <form onChange={form.markDirty} onSubmit={(event) => {
      event.preventDefault(); const operationId = identifier ?? crypto.randomUUID(); setIdentifier(operationId);
      const fields = new FormData(event.currentTarget);
      form.saving.mutate({ operation_id: operationId, configuration_revision: revision, max_pages: Number(fields.get("max_pages")) });
    }}><div className="form-field"><label htmlFor="discovery-max-pages">{t("সর্বোচ্চ কত পাতা সংগ্রহ হবে")}</label><input id="discovery-max-pages" name="max_pages" type="number" required min="1" max={options.maximum_pages} defaultValue={options.default_max_pages} disabled={form.blocked || form.saving.isSuccess} /></div><button className="button" disabled={form.blocked || form.saving.isSuccess}>{t("তালিকা হালনাগাদ করুন")}</button></form>}
    <AccountFeedback error={form.saving.error} />
    {form.saving.isSuccess && <p role="status"><Link className="text-link" href={`/manage/jobs/${form.saving.data.operation_id}/`}>{t("সিঙ্কের অগ্রগতি দেখুন")} →</Link></p>}
    {form.saving.error && identifier && <p><Link className="text-link" href={`/manage/jobs/${identifier}/`}>{t("অনুরোধের অবস্থা দেখুন →")}</Link></p>}
    {!options.active_operation_id && options.latest_operation_id && <p><Link className="text-link" href={`/manage/jobs/${options.latest_operation_id}/`}>{t("সর্বশেষ সিঙ্ক দেখুন")} →</Link></p>}</section>;
}
