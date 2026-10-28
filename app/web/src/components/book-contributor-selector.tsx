"use client";

import { AdminText, useAdminLanguage } from "@/components/admin-language";
import { useId, useState } from "react";
import type { BookRelationships, CatalogReference } from "@/api/types";
import { CatalogReferenceSearch } from "./catalog-reference-search";
import { contributorRoles as roleLabels } from "@/lib/contributor-roles";
import { moveReference } from "@/lib/reference-order";
import { catalogReferenceLabel } from "@/lib/catalog-reference-label";

type Selection = BookRelationships["contributors"][number];


export function BookContributorSelector({ initialSelection, disabled, errors, onChange }: { initialSelection: Selection[]; disabled: boolean; errors?: string[]; onChange: () => void }) {
  const id = useId();
  const { t } = useAdminLanguage();
  const [selected, setSelected] = useState(initialSelection);
  const [role, setRole] = useState<Selection["role"]>("author");
  function accept(entries: Selection[]) { setSelected(entries); onChange(); }
  function choose(entry: CatalogReference) {
    if (!selected.some((value) => value.id === entry.id && value.role === role)) accept([...selected, { ...entry, role }]);
  }
  function move(index: number, offset: number) {
    accept(moveReference(selected, index, offset));
  }
  return <fieldset disabled={disabled}><legend><AdminText>{"লেখক ও সহযোগী"}</AdminText></legend>
    <div className="form-field"><label htmlFor={`${id}-role`}><AdminText>{"যোগ করার ভূমিকা"}</AdminText></label><select id={`${id}-role`} value={role} onChange={(event) => { event.stopPropagation(); setRole(event.target.value as Selection["role"]); }}>
      {Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}
    </select></div>
    <CatalogReferenceSearch kind="contributors" label="সহযোগী" disabled={disabled || selected.length >= 100} excluded={selected.filter((entry) => entry.role === role).map((entry) => entry.id)} onChoose={choose} errors={errors} />
    <input type="hidden" name="contributors" value={JSON.stringify(selected.map(({ id, role }) => ({ id, role })))} />
    <ol className="reference-selection">{selected.map((entry, index) => <li key={`${entry.id}:${entry.role}`}><span>{catalogReferenceLabel(entry)} · <AdminText>{roleLabels[entry.role]}</AdminText></span>
      <div className="editorial-actions"><button className="button button-quiet" type="button" aria-label={`${catalogReferenceLabel(entry)} (${t(roleLabels[entry.role])}): ${t("আগে নিন")}`} disabled={disabled || index === 0} onClick={() => move(index, -1)}><AdminText>{"আগে"}</AdminText></button>
        <button className="button button-quiet" type="button" aria-label={`${catalogReferenceLabel(entry)} (${t(roleLabels[entry.role])}): ${t("পরে নিন")}`} disabled={disabled || index === selected.length - 1} onClick={() => move(index, 1)}><AdminText>{"পরে"}</AdminText></button>
        <button className="button button-quiet" type="button" aria-label={`${catalogReferenceLabel(entry)} (${t(roleLabels[entry.role])}): ${t("নির্বাচন বাদ দিন")}`} onClick={() => accept(selected.filter((_, position) => position !== index))}><AdminText>{"বাদ দিন"}</AdminText></button></div>
    </li>)}</ol>
  </fieldset>;
}
