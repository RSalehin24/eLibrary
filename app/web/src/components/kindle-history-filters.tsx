"use client";

import Link from "next/link";
import { useState } from "react";
import { kindleHistorySorts, type KindleHistoryFilter } from "@/lib/kindle-history";
import { kindleStates } from "@/lib/kindle-status";
import { CatalogFacetInput } from "./catalog-facet-input";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";

export function KindleHistoryFilters({ initial }: { initial: KindleHistoryFilter }) {
  const [filters, setFilters] = useState(initial), { t } = useSiteLanguage();
  const change = (key: keyof KindleHistoryFilter, value: string) => setFilters(previous => ({ ...previous, [key]: value }));
  const active = [initial.q, initial.state, initial.contributor, initial.category, initial.series].some(Boolean);
  return <form action="/kindle/" method="get" className="catalog-filters-form filter-bar kindle-filter-bar" aria-label={t("কিন্ডলের অনুরোধ খুঁজুন")}>
    <div className="filter-search"><label className="visually-hidden" htmlFor="kindle-q"><SiteText>বইয়ের নাম বা কোড</SiteText></label><Icon name="search" /><input id="kindle-q" name="q" type="search" maxLength={120} defaultValue={initial.q} placeholder={t("বইয়ের নাম বা কোড")} /><button className="button"><SiteText>খুঁজুন</SiteText></button></div>
    <label className="filter-sort"><span className="visually-hidden"><SiteText>পাঠানোর অবস্থা</SiteText></span><select aria-label={t("পাঠানোর অবস্থা")} name="state" defaultValue={initial.state ?? ""}><option value=""><SiteText>সব অবস্থা</SiteText></option>{Object.entries(kindleStates).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></label>
    <label className="filter-sort kindle-sort"><span className="visually-hidden"><SiteText>কিন্ডলের অনুরোধ সাজান</SiteText></span><select aria-label={t("কিন্ডলের অনুরোধ সাজান")} name="sort" defaultValue={initial.sort ?? "-sent_at"}>{Object.entries(kindleHistorySorts).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></label>
    <details className="catalog-filter-details"><summary className="button button-quiet"><Icon name="settings" /><SiteText>ফিল্টার</SiteText></summary><div className="catalog-filter-grid">
      <CatalogFacetInput kind="contributors" name="contributor" label="লেখকের নাম" value={filters.contributor ?? ""} onChange={value => change("contributor", value)} />
      <CatalogFacetInput kind="categories" name="category" label="বিভাগের নাম" value={filters.category ?? ""} onChange={value => change("category", value)} />
      <CatalogFacetInput kind="series" name="series" label="সিরিজের নাম" value={filters.series ?? ""} onChange={value => change("series", value)} />
      <button className="button"><SiteText>ফিল্টার প্রয়োগ করুন</SiteText></button>
    </div></details>
    {active && <Link className="filter-clear text-link" href="/kindle/"><Icon name="refresh" /><SiteText>ফিল্টার সরান</SiteText></Link>}
  </form>;
}
