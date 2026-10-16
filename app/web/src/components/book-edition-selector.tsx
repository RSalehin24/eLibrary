"use client";

import { AdminText } from "@/components/admin-language";
import { useState } from "react";
import type { BookRelationships, CatalogReference } from "@/api/types";
import { CatalogReferenceSearch } from "./catalog-reference-search";

export function BookEditionSelector({ relationships, disabled, errors, onChange }: { relationships: BookRelationships; disabled: boolean; errors?: string[]; onChange: () => void }) {
  const [choice, setChoice] = useState<CatalogReference | null | undefined>(undefined);
  return <fieldset disabled={disabled}><legend><AdminText>{"একই কাজের সংস্করণ"}</AdminText></legend>
    <p className="muted"><AdminText>{"অন্য একটি বই বাছলে এই বইটি তার সংস্করণদলে যাবে। নতুন দল তৈরি হলে দুই বই আবার পর্যালোচনা করতে হবে। অনুবাদকে যাচাই ছাড়া একই সংস্করণ হিসেবে বাছবেন না।"}</AdminText></p>
    {relationships.related_editions.length > 0 && <ul>{relationships.related_editions.map((entry) => <li key={entry.id}>{entry.name}</li>)}</ul>}
    {relationships.has_more_editions && <p className="muted"><AdminText>{"প্রথম ১০০টি সম্পর্কিত সংস্করণ দেখানো হচ্ছে।"}</AdminText></p>}
    <CatalogReferenceSearch kind="books" label="অন্য সংস্করণ" disabled={disabled} excluded={[relationships.id]} onChoose={(entry) => { setChoice(entry); onChange(); }} errors={errors} />
    {choice !== undefined && <><input type="hidden" name="edition_of" value={choice?.id ?? ""} /><p role="status">{choice ? `বাছা সংস্করণ: ${choice.name}` : "এই বইটি সংস্করণদল থেকে সরবে।"}</p></>}
    {relationships.group_id && <button className="button button-quiet" type="button" onClick={() => { setChoice(null); onChange(); }}><AdminText>{"এই বইটি সংস্করণদল থেকে সরান"}</AdminText></button>}
    {choice !== undefined && <button className="button button-quiet" type="button" onClick={() => { setChoice(undefined); onChange(); }}><AdminText>{"সংস্করণের নির্বাচন বাতিল করুন"}</AdminText></button>}
  </fieldset>;
}
