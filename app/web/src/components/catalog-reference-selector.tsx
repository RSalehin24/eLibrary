"use client";

import { AdminText } from "@/components/admin-language";
import { useState } from "react";
import type { CatalogReference } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import { CatalogReferenceSearch } from "./catalog-reference-search";
import { moveReference } from "@/lib/reference-order";

type SelectorProps = { kind: EntityKind | "books"; label: string; name: string; initialSelection: CatalogReference[]; disabled: boolean; onChange: () => void; errors?: string[] };

export function CatalogReferenceSelector({ kind, label, name, initialSelection, disabled, onChange, errors }: SelectorProps) {
  const [selected, setSelected] = useState(initialSelection);
  function accept(values: CatalogReference[]) { setSelected(values); onChange(); }
  function move(index: number, offset: number) {
    accept(moveReference(selected, index, offset));
  }
  return <fieldset disabled={disabled}><legend><AdminText>{label}</AdminText></legend>
    <CatalogReferenceSearch kind={kind} label={label} disabled={disabled || selected.length >= 100} excluded={selected.map((entry) => entry.id)} onChoose={(entry) => accept([...selected, entry])} errors={errors} />
    <ol className="reference-selection">{selected.map((entry, index) => <li key={entry.id}>
      <input type="hidden" name={name} value={entry.id} /><span>{entry.name}</span>
      <div className="editorial-actions"><button className="button button-quiet" type="button" aria-label={`${entry.name}: আগে নিন`} disabled={disabled || index === 0} onClick={() => move(index, -1)}><AdminText>{"আগে"}</AdminText></button>
        <button className="button button-quiet" type="button" aria-label={`${entry.name}: পরে নিন`} disabled={disabled || index === selected.length - 1} onClick={() => move(index, 1)}><AdminText>{"পরে"}</AdminText></button>
        <button className="button button-quiet" type="button" aria-label={`${entry.name}: নির্বাচন বাদ দিন`} onClick={() => accept(selected.filter((value) => value.id !== entry.id))}><AdminText>{"বাদ দিন"}</AdminText></button></div>
    </li>)}</ol>
    {selected.length >= 100 && <p role="status"><AdminText>{"সর্বোচ্চ ১০০টি নির্বাচন করা যাবে।"}</AdminText></p>}
  </fieldset>;
}
