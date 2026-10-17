"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { readAutomations } from "@/api/automations";
import type { Automations } from "@/api/types";
import { useAdminLanguage } from "./admin-language";
import { AdminDialog } from "./admin-dialog";
import { AutomationForm } from "./automation-form";

export function SourceScheduling({ initial }: { initial: Automations }) {
  const { t, number } = useAdminLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const [version, setVersion] = useState(0);
  const query = useQuery({ queryKey: ["private", "automations", "list", "page=1"], queryFn: ({ signal }) => readAutomations("page=1", signal), initialData: initial, refetchInterval: 15000, refetchIntervalInBackground: false });
  return <><AdminDialog title="অটোমেশনের সময়সূচি" trigger="সময়সূচি তৈরি করুন" icon="schedule" className="button button-quiet admin-main-action" dialogRef={dialog}><AutomationForm key={version} onSaved={() => { dialog.current?.close(); setVersion((current) => current + 1); }} /></AdminDialog>
    <section className="admin-control-card source-scheduling" aria-label={t("অটোমেশনের সময়সূচি")}>
    {version > 0 && <p role="status">{t("সময়সূচি সংরক্ষিত হয়েছে।")}</p>}
    {query.isError && <p className="field-error" role="alert">{t("হালনাগাদ অবস্থা পাওয়া যায়নি।")} <button className="button button-quiet" onClick={() => void query.refetch()}>{t("আবার দেখুন")}</button></p>}
    <Link className="text-link" href="/manage/automations/">{t("সব সময়সূচি দেখুন")} <span className="status-label">{number(query.data.pagination.total_count)}</span></Link>
  </section></>;
}
