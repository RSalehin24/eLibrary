"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { catalogFilterKeys, catalogHasConditions, catalogSortLabels, type CatalogFilters } from "@/lib/catalog-filters";
import { currentBrowseFilters } from "@/lib/browse-filters";
import { contributorRoles } from "@/lib/contributor-roles";
import { CatalogFacetInput } from "./catalog-facet-input";
import { SavedCatalogFilters } from "./saved-catalog-filters";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";

export function CatalogFiltersForm({ pathname, initial, hidden = {}, onChange, lockedRecordType }: { pathname: string; initial: CatalogFilters; hidden?: CatalogFilters; onChange?: (values: CatalogFilters) => void; lockedRecordType?: "manual" | "digital" }) {
  const id = useId(), { t } = useSiteLanguage();
  const [values, setValues] = useState<Record<string, string>>(currentBrowseFilters(initial));
  const active = catalogFilterKeys.filter(key => !["sort", "record_type"].includes(key) && !!values[key] && values[key] !== "all").length;
  const applied = catalogHasConditions(currentBrowseFilters(initial));
  const changeValues = (next: Record<string, string>) => { setValues(next); onChange?.({ ...next, ...(lockedRecordType ? { record_type: lockedRecordType } : {}) }); };
  const update = (name: string, value: string) => changeValues({ ...values, [name]: value, ...(name === "contributor" && !value ? { contributor_role: "" } : {}) });
  return <div className="catalog-controls"><form action={pathname} role="search" className="catalog-filters-form filter-bar">
    {Object.entries(hidden).map(([name, value]) => <input type="hidden" name={name} value={value} key={name} />)}
    <div className="filter-search"><label className="visually-hidden" htmlFor={`${id}-query`}><SiteText>বই বা লেখকের নাম</SiteText></label><Icon name="search" /><input id={`${id}-query`} name="q" type="search" value={values.q ?? ""} maxLength={120} onChange={(event) => update("q", event.target.value)} placeholder={t("বই বা লেখকের নাম লিখুন")} /><button className="button"><SiteText>খুঁজুন</SiteText></button></div>
    <label className="filter-sort"><span className="visually-hidden"><SiteText>তালিকা সাজান</SiteText></span><select name="sort" aria-label={t("তালিকা সাজান")} value={values.sort ?? ""} onChange={(event) => update("sort", event.target.value)}>{Object.entries(catalogSortLabels).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></label>
    <details className="catalog-filter-details"><summary className="button button-quiet" role="button"><Icon name="settings" /><SiteText>ফিল্টার</SiteText>{active > 0 && <span className="count-badge">{active}</span>}</summary><div className="catalog-filter-grid">
      <CatalogFacetInput kind="contributors" name="contributor" label="লেখক বা সহযোগী" value={values.contributor ?? ""} onChange={(value) => update("contributor", value)} />
      <CatalogFacetInput kind="categories" name="category" label="বিভাগ" value={values.category ?? ""} onChange={(value) => update("category", value)} />
      <CatalogFacetInput kind="series" name="series" label="সিরিজ" value={values.series ?? ""} onChange={(value) => update("series", value)} />
      <CatalogFacetInput kind="collections" name="collection" label="পাঠতালিকা" value={values.collection ?? ""} onChange={(value) => update("collection", value)} />
      {values.contributor && <div className="catalog-filter-field"><label htmlFor={`${id}-role`}><SiteText>ভূমিকা</SiteText></label><select id={`${id}-role`} name="contributor_role" value={values.contributor_role ?? ""} onChange={(event) => update("contributor_role", event.target.value)}><option value=""><SiteText>সব ভূমিকা</SiteText></option>{Object.entries(contributorRoles).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div>}
      {pathname === "/my-books/" && <div className="catalog-filter-field"><label htmlFor={`${id}-ownership`}><SiteText>নিজের সংগ্রহ</SiteText></label><select id={`${id}-ownership`} name="ownership" value={values.ownership ?? ""} onChange={(event) => update("ownership", event.target.value)}><option value=""><SiteText>সব বই</SiteText></option><option value="mine"><SiteText>আমার সংগ্রহের বই</SiteText></option></select></div>}
      <button className="button filter-apply"><SiteText>ফিল্টার প্রয়োগ করুন</SiteText></button>
    </div></details>
    {(applied || catalogHasConditions(values)) && <Link className="filter-clear text-link" href={`${pathname}${hidden.view ? `?view=${encodeURIComponent(hidden.view)}` : ""}`} onNavigate={() => { if (!applied) changeValues({}); }}><Icon name="refresh" /><SiteText>ফিল্টার সরান</SiteText></Link>}
  </form>{!lockedRecordType && <SavedCatalogFilters pathname={pathname} values={values} hidden={hidden} />}</div>;
}
