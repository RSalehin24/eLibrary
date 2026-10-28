"use client";

import { AdminText } from "@/components/admin-language";
import { useState } from "react";
import type { BookRelationships, CatalogReference } from "@/api/types";
import { CatalogReferenceSearch } from "./catalog-reference-search";

export function BookEditionSelector({ relationships, disabled, errors, onChange }: { relationships: BookRelationships; disabled: boolean; errors?: string[]; onChange: () => void }) {
  const [choice, setChoice] = useState<CatalogReference | null | undefined>(undefined);
  return <fieldset disabled={disabled}><legend><AdminText>{"একই কাজের সংস্করণ"}</AdminText></legend>
    <p className="muted"><AdminText>{"অন্য বই বেছে নিলে বইটি একই সংস্করণের দলে যুক্ত হবে। যুক্ত করার আগে বই ও অনুবাদের পরিচয় মিলিয়ে নিন।"}</AdminText></p>
    {relationships.related_editions.length > 0 && <ul>{relationships.related_editions.map((entry) => <li key={entry.id}>{entry.name}</li>)}</ul>}
    {relationships.has_more_editions && <p className="muted"><AdminText>{"প্রথম ১০০টি সম্পর্কিত সংস্করণ দেখানো হচ্ছে।"}</AdminText></p>}
    <CatalogReferenceSearch kind="books" label="অন্য সংস্করণ" disabled={disabled} excluded={[relationships.id]} onChoose={(entry) => { setChoice(entry); onChange(); }} errors={errors} />
    {choice !== undefined && <><input type="hidden" name="edition_of" value={choice?.id ?? ""} /><p role="status">{choice ? <><AdminText>{"বাছা সংস্করণ:"}</AdminText> {choice.name}</> : <AdminText>{"এই বইটি সংস্করণদল থেকে সরবে।"}</AdminText>}</p></>}
    {relationships.group_id && <button className="button button-quiet" type="button" onClick={() => { setChoice(null); onChange(); }}><AdminText>{"এই বইটি সংস্করণদল থেকে সরান"}</AdminText></button>}
    {choice !== undefined && <button className="button button-quiet" type="button" onClick={() => { setChoice(undefined); onChange(); }}><AdminText>{"সংস্করণের নির্বাচন বাতিল করুন"}</AdminText></button>}
  </fieldset>;
}
