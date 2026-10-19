"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { SourceEntry } from "@/api/types";
import { sourceStatus } from "@/lib/source-status";
import { catalogStateLabel } from "@/lib/catalog-state";
import { useAdminLanguage } from "./admin-language";
import { SourceUpdateStatus } from "./source-update-status";

type Props = {
  entries: SourceEntry[];
  selected: ReadonlySet<string>;
  blocked: boolean;
  limitReached: boolean;
  onToggle: (entry: SourceEntry) => void;
  onTogglePage: () => void;
  onCreate: (entry: SourceEntry) => void;
  toolbar: ReactNode;
};

export function SourceTable(props: Props) {
  const { t } = useAdminLanguage();
  const selectAll = useRef<HTMLInputElement>(null);
  const available = props.entries.filter((entry) => entry.can_process || props.selected.has(entry.id));
  const checked = available.length > 0 && available.every((entry) => props.selected.has(entry.id));
  const partial = !checked && available.some((entry) => props.selected.has(entry.id));
  useEffect(() => { if (selectAll.current) selectAll.current.indeterminate = partial; }, [partial]);
  return <table className="source-table"><caption><div className="source-table-toolbar"><label className="checkbox-field"><input ref={selectAll} type="checkbox" checked={checked} disabled={props.blocked || !available.length || (!checked && props.limitReached)} onChange={props.onTogglePage} />{t("এই পাতার সব বই নির্বাচন করুন")}</label>{props.toolbar}</div></caption>
    <thead><tr><th scope="col"><span className="visually-hidden">{t("নির্বাচন করুন")}</span></th>
      <th scope="col">{t("বইয়ের নাম")}</th><th scope="col">{t("লেখক")}</th><th scope="col">{t("অবস্থা")}</th><th scope="col">{t("করণীয়")}</th></tr></thead>
    <tbody>{props.entries.map((entry) => <tr className="source-row" key={entry.id}>
      <td className="source-check"><label className="source-select-control"><input type="checkbox" checked={props.selected.has(entry.id)} disabled={props.blocked || (!props.selected.has(entry.id) && (!entry.can_process || props.limitReached))} onChange={() => props.onToggle(entry)} aria-label={`${entry.title} — ${t("নির্বাচন করুন")}`} /></label></td>
      <td className="source-title"><h2><Link href={`/manage/sources/${entry.id}/`}>{entry.title}</Link></h2><SourceUpdateStatus entry={entry} /></td>
      <td data-label={t("লেখক")}>{entry.author_line || t("লেখকের তথ্য নেই")}</td>
      <td data-label={t("অবস্থা")}><span className="status-label">{t(entry.active_operation_id ? "কাজ চলছে" : entry.book && !entry.book.deleted_at ? catalogStateLabel(entry.book.state) : sourceStatus(entry))}</span></td>
      <td className="source-row-actions"><SourceRowAction entry={entry} blocked={props.blocked || (props.limitReached && !props.selected.has(entry.id))} onCreate={props.onCreate} /><Link className="text-link" href={`/manage/sources/${entry.id}/`}>{t(entry.book && !entry.book.deleted_at ? "বইয়ের ফাইল" : "বিস্তারিত")}</Link></td>
    </tr>)}</tbody></table>;
}

function SourceRowAction({ entry, blocked, onCreate }: Pick<Props, "blocked" | "onCreate"> & { entry: SourceEntry }) {
  const { t } = useAdminLanguage();
  const job = entry.active_operation_id || entry.latest_operation_id;
  if (entry.book && !entry.book.deleted_at) return <>{entry.can_edit_book && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(entry.book.slug)}/`}>{t("বইয়ের তথ্য সম্পাদনা করুন")}</Link>}{job && <Link className="text-link" href={`/manage/jobs/${job}/`}>{t("কাজ দেখুন")}</Link>}</>;
  if (job) return <Link className="text-link" href={`/manage/jobs/${job}/`}>{t("কাজ দেখুন")}</Link>;
  if (!entry.can_process) return <span className="muted">{t("এই লিংক থেকে বই তৈরি করা যাবে না")}</span>;
  return <button type="button" className="button button-quiet" disabled={blocked} onClick={() => onCreate(entry)}>{t("বই তৈরি করুন")}</button>;
}
