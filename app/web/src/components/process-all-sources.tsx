"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { processAllSources, readCatalogProcessing } from "@/api/source-processing";
import type { CatalogProcessingCommand, CatalogProcessingOptions } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { AdminDialog } from "./admin-dialog";
import { SourceOperation } from "./source-operation";
import { useAdminLanguage } from "./admin-language";

export function ProcessAllSources({ initial }: { initial: CatalogProcessingOptions }) {
  const { t, number } = useAdminLanguage();
  const client = useQueryClient();
  const dialog = useRef<HTMLDialogElement>(null);
  const [identifier, setIdentifier] = useState<string | null>(null), [accepted, setAccepted] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["private", "catalog-processing"], queryFn: ({ signal }) => readCatalogProcessing(signal), initialData: initial, refetchInterval: 15000, refetchIntervalInBackground: false });
  const options = query.data;
  const form = useManagedForm((values: CatalogProcessingCommand) => processAllSources(values), async (result) => { setAccepted(result.operation_id); setIdentifier(null); dialog.current?.close(); await client.invalidateQueries({ queryKey: ["private", "catalog-processing"] }); });
  const operation = options.active_operation_id ?? accepted ?? options.latest_operation_id;
  return <><AdminDialog title="সব বই তৈরি করুন" dialogRef={dialog} trigger="সব বই তৈরি করুন" icon="books" className="button admin-main-action" disabled={form.blocked || !!options.active_operation_id || !options.configuration_revision || !options.eligible_sources || query.isError}>
      <p>{t("এই তালিকার সব যোগ্য বইয়ের কাজ শুরু হবে। তৈরি বই, চলমান কাজ এবং অমীমাংসিত সমস্যা বাদ যাবে।")}</p><p className="control-stat">{number(options.eligible_sources)} <span>{t("তৈরির জন্য বাকি বই")}</span></p>
      <button type="button" className="button" disabled={form.blocked} onClick={() => { if (!options.configuration_revision) return; const id = identifier ?? crypto.randomUUID(); setIdentifier(id); form.saving.mutate({ operation_id: id, configuration_revision: options.configuration_revision }); }}>{t("সব বইয়ের কাজ তালিকায় যোগ করুন")}</button><AccountFeedback error={form.saving.error} />
      {form.saving.isSuccess && <p role="status">{t("বই তৈরি শুরু হয়েছে।")}</p>}
    </AdminDialog>
    <section className="admin-control-card process-all" aria-label={t("বই তৈরি")}><p className="control-stat"><strong>{number(options.eligible_sources)}</strong> <span>{t("তৈরির জন্য বাকি বই")}</span></p>
    {query.isError && <p className="field-error" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void query.refetch()}>{t("আবার দেখুন")}</button></p>}
    <AccountFeedback error={form.saving.error} />{form.saving.error && identifier && <Link className="text-link" href={`/manage/jobs/${identifier}/`}>{t("এই অনুরোধের ফল দেখুন")}</Link>}
    {operation && <SourceOperation id={operation} />}
  </section></>;
}
