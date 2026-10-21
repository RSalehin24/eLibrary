"use client";

import Link from "next/link";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { runAutomationNow } from "@/api/automations";
import type { AutomationRunCommand, SourceAutomation } from "@/api/types";
import { automationErrors } from "@/lib/automation-status";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { useAdminLanguage } from "./admin-language";
import { Icon } from "./icon";

export function AutomationRunNow({ automation }: { automation: SourceAutomation }) {
  const { t } = useAdminLanguage();
  return <section className="account-section" aria-label={t("সময়সূচি এখনই চালান")}><h2>{t("সময়সূচি এখনই চালান")}</h2><p>{t("সংরক্ষিত সেটিংস দিয়ে একবার কাজ চলবে। পরের নির্ধারিত সময় বদলাবে না।")}</p><AutomationRunAction automation={automation} /></section>;
}

export function AutomationRunAction({ automation }: { automation: SourceAutomation }) {
  const { t } = useAdminLanguage(), client = useQueryClient();
  const [identifier, setIdentifier] = useState<string | null>(null);
  const form = useManagedForm((values: AutomationRunCommand) => runAutomationNow(automation.id, values), async () => { await client.invalidateQueries({ queryKey: ["private", "automations", automation.id, "runs"] }); });
  const result = form.saving.data;
  return <div className="automation-run-action">
    {!result && <form onSubmit={(event) => { event.preventDefault(); form.markDirty(); const operation = identifier ?? crypto.randomUUID(); setIdentifier(operation); form.saving.mutate({ operation_id: operation, expected_updated_at: automation.updated_at }); }}><button className="button" disabled={form.blocked}><Icon name="play" />{t("এখনই চালান")}</button></form>}
    <AccountFeedback error={form.saving.error} />
    {form.saving.error && <button className="button button-quiet" type="button" onClick={reloadManagedForm}>{t("বর্তমান তথ্য খুলুন")}</button>}
    {result && <p role="status">{t(result.state === "queued" ? "কাজ যোগ হয়েছে। অগ্রগতি ও নিয়ন্ত্রণ দেখুন।" : automationErrors[result.error_code] ?? "এইবারের কাজ শুরু করা যায়নি। কনফিগারেশন ও অনুমতি পরীক্ষা করুন।")}</p>}
    {result?.job_id && <Link className="button button-quiet" href={`/manage/jobs/${result.job_id}/`}>{t("কাজের অগ্রগতি দেখুন")}</Link>}
  </div>;
}
