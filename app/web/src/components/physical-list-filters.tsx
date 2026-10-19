"use client";

import { Icon } from "./icon";
import { useSiteLanguage } from "./site-language";
import { CatalogFacetInput } from "./catalog-facet-input";
import { useId, useState } from "react";

export function PhysicalListFilters({ filters }: { filters: Readonly<Record<string, string>> }) {
  const { language } = useSiteLanguage();
  const id = useId();
  const [values, setValues] = useState({ writer: filters.writer, translator: filters.translator, editor: filters.editor });
  const text = (bn: string, en: string) => language === "bn" ? bn : en;
  return <form className="catalog-filter-grid" action="/physical-books/" aria-label={text("কাগজের বইয়ের ফিল্টার", "Physical book filters")}>
    {Object.entries(filters).filter(([key]) => !["writer", "translator", "editor", "publisher", "binding", "language"].includes(key)).map(([key, value]) => <input key={key} type="hidden" name={key} value={value} />)}
    {Object.entries({ writer: "লেখক", translator: "অনুবাদক", editor: "সম্পাদক" }).map(([name, label]) => <CatalogFacetInput key={name} kind="contributors" name={name} label={label} value={values[name as keyof typeof values] ?? ""} onChange={value => setValues(current => ({ ...current, [name]: value }))} />)}
    <div className="catalog-filter-field"><label htmlFor={`${id}-publisher`}>{text("প্রকাশক", "Publisher")}</label><input id={`${id}-publisher`} name="publisher" defaultValue={filters.publisher} maxLength={255} /></div>
    <div className="catalog-filter-field"><label htmlFor={`${id}-binding`}>{text("বাঁধাই", "Binding")}</label><select id={`${id}-binding`} name="binding" defaultValue={filters.binding}>
      <option value="">{text("সব বাঁধাই", "All bindings")}</option><option value="hard_cover">{text("শক্ত মলাট", "Hardcover")}</option><option value="paper_back">{text("পেপারব্যাক", "Paperback")}</option>
    </select></div>
    <div className="catalog-filter-field"><label htmlFor={`${id}-language`}>{text("বইয়ের ভাষা", "Book language")}</label><select id={`${id}-language`} name="language" defaultValue={filters.language}>
      <option value="">{text("সব ভাষা", "All languages")}</option><option value="bn">বাংলা</option><option value="en">English</option>
    </select></div><button className="button button-quiet"><Icon name="search" />{text("ফিল্টার করুন", "Apply filters")}</button>
  </form>;
}
