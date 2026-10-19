"use client";

import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/api/http";
import type { EntityCollection } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import { useDebouncedQuery } from "@/lib/debounced-query";
import { SiteText } from "./site-language";

export function CatalogFacetInput({ kind, name, label, value, onChange }: { kind: EntityKind; name: string; label: string; value: string; onChange: (value: string) => void }) {
  const id = useId(), query = useDebouncedQuery(value);
  const [active, setActive] = useState(false);
  const suggestions = useQuery({ queryKey: ["public", "facet-suggestions", kind, query], queryFn: ({ signal }) => apiRequest<EntityCollection>(`catalog/entities/${kind}/?${new URLSearchParams({ q: query, limit: "24" })}`, { signal }), enabled: active || !!value, refetchOnWindowFocus: false });
  return <div className="catalog-filter-field"><label htmlFor={id}><SiteText>{label}</SiteText></label>
    <input id={id} name={name} list={`${id}-options`} value={value} maxLength={255} autoComplete="off" onFocus={() => setActive(true)} onChange={(event) => onChange(event.target.value)} aria-describedby={suggestions.isError ? `${id}-error` : undefined} />
    <datalist id={`${id}-options`}>{suggestions.data?.entries.map((entry) => <option value={entry.name} key={entry.id} />)}</datalist>
    {suggestions.isError && <small id={`${id}-error`}><SiteText>নামের সাজেশন পাওয়া যায়নি। নাম লিখে খুঁজতে পারবেন।</SiteText></small>}
  </div>;
}
