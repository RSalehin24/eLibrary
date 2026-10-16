"use client";

import { AdminText } from "@/components/admin-language";
import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { readCatalogReferences } from "@/api/entities";
import type { CatalogReference } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import { useDebouncedQuery } from "@/lib/debounced-query";

type SearchProps = { kind: EntityKind | "books"; label: string; disabled: boolean; excluded?: string[]; onChoose: (entry: CatalogReference) => void; errors?: string[] };

export function CatalogReferenceSearch({ kind, label, disabled, excluded = [], onChoose, errors }: SearchProps) {
  const id = useId();
  const [search, setSearch] = useState("");
  const query = useDebouncedQuery(search);
  const references = useQuery({ queryKey: ["private", "catalog-references", kind, query], queryFn: ({ signal }) => readCatalogReferences(kind, query, signal), refetchOnWindowFocus: false });
  return <>
    <div className="form-field"><label htmlFor={`${id}-search`}><AdminText>{label}</AdminText><AdminText>{": নাম খুঁজুন"}</AdminText></label>
      <input id={`${id}-search`} value={search} disabled={disabled} maxLength={120} onChange={(event) => { event.stopPropagation(); setSearch(event.target.value); }} /></div>
    {references.isFetching && <p role="status"><AdminText>{"খোঁজা হচ্ছে…"}</AdminText></p>}
    {references.isError && <p role="alert" className="field-error"><AdminText>{"তালিকা পাওয়া যায়নি। "}</AdminText><button className="button button-quiet" type="button" onClick={() => void references.refetch()}><AdminText>{"আবার খুঁজুন"}</AdminText></button></p>}
    <div className="form-field"><label htmlFor={`${id}-select`}><AdminText>{label}</AdminText><AdminText>{": যোগ করুন"}</AdminText></label>
      <select id={`${id}-select`} value="" disabled={disabled || search !== query || references.isFetching || references.isError} aria-invalid={!!errors?.length} aria-describedby={errors?.length ? `${id}-error` : undefined} onChange={(event) => {
        const entry = references.data?.entries.find((value) => value.id === event.target.value);
        if (entry) onChoose(entry);
      }}><option value=""><AdminText>{"একটি বেছে নিন"}</AdminText></option>
        {references.data?.entries.filter((entry) => !excluded.includes(entry.id)).map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
      </select></div>
    {references.data?.has_more && <p className="muted"><AdminText>{"প্রথম ২৪টি ফল দেখানো হচ্ছে। আরও নির্দিষ্ট নাম দিয়ে খুঁজুন।"}</AdminText></p>}
    {!references.isFetching && !references.isError && !references.data?.entries.length && <p className="muted"><AdminText>{"এই নামে কোনো ফল পাওয়া যায়নি।"}</AdminText></p>}
    {errors?.length ? <p id={`${id}-error`} className="field-error" role="alert">{errors.join(" ")}</p> : null}
  </>;
}
