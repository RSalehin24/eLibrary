"use client";

import Link from "next/link";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { processSourceSelection } from "@/api/source-processing";
import type { SourceBulkCommand, SourceEntry } from "@/api/types";
import { reloadManagedForm, useManagedForm } from "@/lib/managed-form";
import { useUnsavedChanges } from "@/lib/unsaved-changes";
import { AccountFeedback } from "./account-feedback";
import { SourceTable } from "./source-table";
import { useAdminLanguage } from "./admin-language";
import { sourceSelectionLimit, toggleSourcePage, type SelectedSource } from "@/lib/source-selection";

export function SourceSelection({ entries }: { entries: SourceEntry[] }) {
  const { t, number } = useAdminLanguage();
  const client = useQueryClient(), [selected, setSelected] = useState<Record<string, SelectedSource>>({});
  const [submitted, setSubmitted] = useState<Record<string, SelectedSource>>({});
  const values = Object.values(selected);
  const form = useManagedForm((command: SourceBulkCommand) => processSourceSelection(command), async (result) => {
    setSelected((current) => Object.fromEntries(Object.entries(current).filter(([id]) => !result.entries.some((outcome) => outcome.source_id === id && outcome.accepted))));
    await client.invalidateQueries({ queryKey: ["private", "sources"] });
    await client.invalidateQueries({ queryKey: ["private", "jobs"] });
  });
  useUnsavedChanges(values.length > 0);
  const toggle = (entry: SourceEntry) => setSelected((current) => {
    const next = { ...current };
    if (next[entry.id]) delete next[entry.id];
    else next[entry.id] = { entry, operationId: crypto.randomUUID() };
    return next;
  });
  function submit(requested: Record<string, SelectedSource>) {
    if (form.blocked) return;
    setSelected((current) => ({ ...current, ...requested })); setSubmitted(requested);
    form.saving.mutate({ entries: Object.values(requested).map(({ entry, operationId }) => ({ source_id: entry.id, operation_id: operationId, expected_updated_at: entry.updated_at })) });
  }
  function togglePage() {
    setSelected((current) => toggleSourcePage(current, entries));
  }
  const toolbar = values.length > 0 && <section className="source-selection-bar" aria-label={t("নির্বাচিত বই তৈরি করুন")}><p>{t("নির্বাচিত")}: {number(values.length)} / {number(sourceSelectionLimit)}</p>
    <button type="button" className="button" disabled={!values.length || form.blocked} onClick={() => submit(selected)}>{t("নির্বাচিত বই তৈরি করুন")}</button>
    {!!values.length && <button type="button" className="button button-quiet" disabled={form.blocked} onClick={() => setSelected({})}>{t("নির্বাচন সরান")}</button>}
    </section>;
  return <>
    <AccountFeedback error={form.saving.error} />
    {form.saving.data && <div className="notice" role="status"><p>{t(form.saving.data.entries.some((outcome) => !outcome.accepted) ? "যে বইগুলো তৈরি শুরু হয়নি, সেগুলো নির্বাচিত আছে।" : "বই তৈরি শুরু হয়েছে।")}</p><ul>{form.saving.data.entries.map((outcome) => <li key={outcome.source_id}>{submitted[outcome.source_id]?.entry.title} · {outcome.accepted ? <Link className="text-link" href={`/manage/jobs/${outcome.operation_id}/`}>{t("সংরক্ষিত কাজ দেখুন →")}</Link> : <span>{t("অনুরোধ হয়নি")}: {outcome.error?.detail}</span>}</li>)}</ul></div>}
    {form.saving.error && <><p className="notice">{t("ফল নিশ্চিত নয়। আবার জমা দেওয়ার আগে কাজের অবস্থা দেখুন।")}</p><ul>{Object.values(submitted).map(({ entry, operationId }) => <li key={entry.id}>{entry.title} <Link className="text-link" href={`/manage/jobs/${operationId}/`}>{t("অনুরোধের অবস্থা দেখুন →")}</Link></li>)}</ul><button type="button" className="button button-quiet" onClick={reloadManagedForm}>{t("বর্তমান তালিকা খুলুন")}</button></>}
    <SourceTable toolbar={toolbar} entries={entries} selected={new Set(Object.keys(selected))} blocked={form.blocked} limitReached={values.length >= sourceSelectionLimit} onToggle={toggle} onTogglePage={togglePage} onCreate={(entry) => submit({ [entry.id]: selected[entry.id] ?? { entry, operationId: crypto.randomUUID() } })} /></>;
}
