"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { discoverSources, readDiscoveryOptions } from "@/api/source-processing";
import type { SourceDiscoveryCommand, SourceDiscoveryOptions } from "@/api/types";
import { useManagedForm } from "@/lib/managed-form";
import { AccountFeedback } from "./account-feedback";
import { useAdminLanguage } from "./admin-language";
import { SourceOperation } from "./source-operation";
import { Icon } from "./icon";

export function SourceDiscovery({ options: initial, catalogScope = "all" }: { options: SourceDiscoveryOptions; catalogScope?: "all" | "unfinished" }) {
  const { t } = useAdminLanguage();
  const client = useQueryClient();
  const [identifier, setIdentifier] = useState<string | null>(null), [accepted, setAccepted] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["private", "discovery-options", catalogScope], queryFn: ({ signal }) => readDiscoveryOptions(signal, catalogScope), initialData: initial, refetchInterval: 15000, refetchIntervalInBackground: false });
  const options = query.data;
  const form = useManagedForm((values: SourceDiscoveryCommand) => discoverSources(values), async (result) => { setAccepted(result.operation_id); setIdentifier(null); await client.invalidateQueries({ queryKey: ["private", "discovery-options"] }); });
  const revision = options.configuration_revision;
  function submit(values: Pick<SourceDiscoveryCommand, "max_pages" | "fetch_all">) {
    if (!revision || form.blocked) return;
    const operationId = identifier ?? crypto.randomUUID(); setIdentifier(operationId);
    form.saving.mutate({ operation_id: operationId, configuration_revision: revision, catalog_scope: catalogScope, ...values });
  }
  const blocked = form.blocked || !!options.active_operation_id || !options.configured || !revision || query.isError;
  const operation = options.active_operation_id ?? accepted ?? options.latest_operation_id;
  return <><button type="button" className="button button-quiet admin-main-action" disabled={blocked} onClick={() => submit({ max_pages: options.maximum_pages, fetch_all: true })}><Icon name="download" />{t("সব বইয়ের তথ্য আনুন")}</button>
    <section className="admin-control-card source-sync" aria-label={t("বইয়ের তালিকা")}>
    <details className="source-advanced"><summary>{t("সীমিত সংগ্রহ")}</summary><form className="limited-fetch" onChange={form.markDirty} onSubmit={(event) => { event.preventDefault(); submit({ max_pages: Number(new FormData(event.currentTarget).get("max_pages")), fetch_all: false }); }}>
      <label className="visually-hidden" htmlFor="discovery-max-pages">{t("সর্বোচ্চ কত পাতা সংগ্রহ হবে")}</label><div><input id="discovery-max-pages" name="max_pages" type="number" required min="1" max={options.maximum_pages} defaultValue={options.default_max_pages} disabled={blocked} /><button className="button button-quiet" disabled={blocked}>{t("কয়েকটি পাতা আনুন")}</button></div>
    </form></details>
    {!options.configured && <p className="notice">{t("বইয়ের তালিকা সংগ্রহ করতে ওয়েবসাইটের সেটিংস ঠিক করতে হবে।")}</p>}
    {query.isError && <p className="field-error" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void query.refetch()}>{t("আবার দেখুন")}</button></p>}
    <AccountFeedback error={form.saving.error} />
    {form.saving.error && identifier && <Link className="text-link" href={`/manage/jobs/${identifier}/`}>{t("অনুরোধের অবস্থা দেখুন →")}</Link>}
    {operation && <details className="source-operation-receipt" open={!!options.active_operation_id || !!accepted}><summary>{t("তথ্য আনা")}</summary><SourceOperation id={operation} /></details>}
  </section></>;
}
