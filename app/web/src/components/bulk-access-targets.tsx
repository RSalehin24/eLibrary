"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readAccessReferences } from "@/api/managed-access";
import type { AccessReferenceKind } from "@/api/types";
import { maximumBulkTargets, type BulkAccessTarget } from "@/lib/bulk-access";
import { useDebouncedQuery } from "@/lib/debounced-query";
import { AdminNumber, AdminText, useAdminLanguage } from "./admin-language";

type Props = { kind: AccessReferenceKind; disabled: boolean; selected: BulkAccessTarget[]; onChange: (targets: BulkAccessTarget[]) => void };

export function BulkAccessTargets({ kind, disabled, selected, onChange }: Props) {
  const [search, setSearch] = useState("");
  const query = useDebouncedQuery(search);
  const { t } = useAdminLanguage();
  const references = useQuery({ queryKey: ["private", "access", "references", kind, query], queryFn: ({ signal }) => readAccessReferences(kind, query, signal), refetchOnWindowFocus: false });
  const pending = search !== query || references.isFetching;
  function toggle(entry: BulkAccessTarget) {
    onChange(selected.some((target) => target.id === entry.id) ? selected.filter((target) => target.id !== entry.id) : [...selected, entry]);
  }
  return <fieldset className="bulk-access-targets"><legend><AdminText>{"২. বই, বিভাগ বা লেখক নির্বাচন করুন"}</AdminText></legend>
    <label htmlFor="bulk-target-search"><AdminText>{"একাধিক লক্ষ্যের জন্য খুঁজুন"}</AdminText></label>
    <input id="bulk-target-search" type="search" maxLength={200} value={search} disabled={disabled} onChange={(event) => setSearch(event.target.value)} />
    <p className="muted"><AdminText>{"নির্বাচিত: "}</AdminText><AdminNumber value={selected.length} /><AdminText>{" / সর্বোচ্চ ২০টি। অন্য নাম খুঁজলেও নির্বাচন থাকবে।"}</AdminText></p>
    {!!selected.length && <ul className="bulk-access-selected">{selected.map((target) => <li key={target.id}><span>{target.name}</span><button type="button" className="button button-quiet" disabled={disabled} aria-label={`${t("নির্বাচন সরান")}: ${target.name}`} onClick={() => toggle(target)}><AdminText>{"সরান"}</AdminText></button></li>)}</ul>}
    {pending && <p role="status"><AdminText>{"খোঁজা হচ্ছে…"}</AdminText></p>}
    {references.isError && <p role="alert"><AdminText>{"তালিকা পাওয়া যায়নি। "}</AdminText><button type="button" className="button button-quiet" disabled={disabled} onClick={() => void references.refetch()}><AdminText>{"আবার খুঁজুন"}</AdminText></button></p>}
    {!references.isError && <div className="bulk-access-options" aria-busy={pending}>{references.data?.entries.map((entry) => {
      const checked = selected.some((target) => target.id === entry.id);
      return <label className="check-field" key={entry.id}><input type="checkbox" checked={checked} disabled={disabled || pending || (!checked && selected.length >= maximumBulkTargets)} onChange={() => toggle(entry)} /><span>{entry.name}</span></label>;
    })}</div>}
    {!pending && !references.isError && !references.data?.entries.length && <p><AdminText>{"এই নামে কোনো লক্ষ্য পাওয়া যায়নি।"}</AdminText></p>}
    {!!references.data?.pagination.total_count && <p className="muted"><AdminText>{"প্রথম ২৪টি ফল দেখানো হচ্ছে। আরও নির্দিষ্ট নাম দিয়ে খুঁজতে পারেন।"}</AdminText></p>}
  </fieldset>;
}
