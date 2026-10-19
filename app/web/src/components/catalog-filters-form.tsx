"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { catalogFilterKeys, catalogSortLabels, type CatalogFilters } from "@/lib/catalog-filters";
import { contributorRoles } from "@/lib/contributor-roles";
import { CatalogFacetInput } from "./catalog-facet-input";
import { SavedCatalogFilters } from "./saved-catalog-filters";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";

export function CatalogFiltersForm({ pathname, initial, hidden = {}, onChange, lockedRecordType }: { pathname: string; initial: CatalogFilters; hidden?: CatalogFilters; onChange?: (values: CatalogFilters) => void; lockedRecordType?: "manual" | "digital" }) {
  const id = useId(), { t } = useSiteLanguage();
  const [values, setValues] = useState<Record<string, string>>({ record_type: "all", ...initial, ...(lockedRecordType ? { record_type: lockedRecordType } : {}) });
  const active = catalogFilterKeys.filter(key => key !== "sort" && !(lockedRecordType && key === "record_type") && !!values[key] && values[key] !== "all").length;
  const update = (name: string, value: string) => { const next = { ...values, [name]: value }; setValues(next); onChange?.(next); };
  return <>{!lockedRecordType && <SavedCatalogFilters pathname={pathname} values={values} hidden={hidden} />}<form action={pathname} role="search" className="catalog-filters-form">
    {Object.entries(hidden).map(([name, value]) => <input type="hidden" name={name} value={value} key={name} />)}
    <div className="search-form"><label className="visually-hidden" htmlFor={`${id}-query`}><SiteText>বই বা লেখকের নাম</SiteText></label><input id={`${id}-query`} name="q" value={values.q ?? ""} maxLength={120} onChange={(event) => update("q", event.target.value)} placeholder={t("বই বা লেখকের নাম লিখুন")} /><button className="button"><Icon name="search" /><SiteText>খুঁজুন</SiteText></button></div>
    <div className="catalog-filter-toolbar"><div className="catalog-filter-field"><label htmlFor={`${id}-sort`}><SiteText>তালিকা সাজান</SiteText></label><select id={`${id}-sort`} name="sort" value={values.sort ?? ""} onChange={(event) => update("sort", event.target.value)}>{Object.entries(catalogSortLabels).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div></div>
    <details className="catalog-filter-details" open={active > 0}><summary className="button button-quiet" role="button"><Icon name="settings" /><SiteText>ফিল্টার</SiteText>{active > 0 && <span>{active}</span>}</summary><div className="catalog-filter-grid">
      <CatalogFacetInput kind="contributors" name="contributor" label="লেখক বা সহযোগী" value={values.contributor ?? ""} onChange={(value) => update("contributor", value)} />
      <CatalogFacetInput kind="categories" name="category" label="বিভাগ" value={values.category ?? ""} onChange={(value) => update("category", value)} />
      <CatalogFacetInput kind="series" name="series" label="সিরিজ" value={values.series ?? ""} onChange={(value) => update("series", value)} />
      <CatalogFacetInput kind="collections" name="collection" label="সংগ্রহ" value={values.collection ?? ""} onChange={(value) => update("collection", value)} />
      <div className="catalog-filter-field"><label htmlFor={`${id}-role`}><SiteText>ভূমিকা</SiteText></label><select id={`${id}-role`} name="contributor_role" value={values.contributor_role ?? ""} onChange={(event) => update("contributor_role", event.target.value)}><option value=""><SiteText>সব ভূমিকা</SiteText></option>{Object.entries(contributorRoles).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div>
      {lockedRecordType ? <input type="hidden" name="record_type" value={lockedRecordType} /> : <div className="catalog-filter-field"><label htmlFor={`${id}-type`}><SiteText>বইয়ের ধরন</SiteText></label><select id={`${id}-type`} name="record_type" value={values.record_type} onChange={(event) => update("record_type", event.target.value)}><option value="all"><SiteText>সব ধরনের বই</SiteText></option><option value="digital"><SiteText>ডিজিটাল বই</SiteText></option><option value="manual"><SiteText>কাগজের বই</SiteText></option></select></div>}
      <div className="catalog-filter-field"><label htmlFor={`${id}-ownership`}><SiteText>নিজের সংগ্রহ</SiteText></label><select id={`${id}-ownership`} name="ownership" value={values.ownership ?? ""} onChange={(event) => update("ownership", event.target.value)}><option value=""><SiteText>সব বই</SiteText></option><option value="mine"><SiteText>আমার সংগ্রহের বই</SiteText></option></select></div>

    </div></details>
    <Link className="text-link" href={`${pathname}${hidden.view ? `?view=${encodeURIComponent(hidden.view)}` : ""}`}><Icon name="refresh" /><SiteText>সব ফিল্টার মুছুন</SiteText></Link>
  </form></>;
}
