"use client";

import Link from "next/link";
import { useState } from "react";
import { kindleHistorySorts, type KindleHistoryFilter } from "@/lib/kindle-history";
import { kindleStates } from "@/lib/kindle-status";
import { CatalogFacetInput } from "./catalog-facet-input";
import { SiteText, useSiteLanguage } from "./site-language";

export function KindleHistoryFilters({ initial }: { initial: KindleHistoryFilter }) {
  const [filters, setFilters] = useState(initial);
  const { t } = useSiteLanguage();
  const change = (key: keyof KindleHistoryFilter, value: string) => setFilters((previous) => ({ ...previous, [key]: value }));
  return <form action="/kindle/" method="get" className="catalog-filters-form" aria-label={t("কিন্ডলের অনুরোধ খুঁজুন")}>
    <div className="catalog-filter-grid"><div className="catalog-filter-field"><label htmlFor="kindle-q"><SiteText>বইয়ের নাম বা কোড</SiteText></label><input id="kindle-q" name="q" type="search" maxLength={120} defaultValue={initial.q} /></div>
      <CatalogFacetInput kind="contributors" name="contributor" label="লেখকের নাম" value={filters.contributor ?? ""} onChange={(value) => change("contributor", value)} />
      <CatalogFacetInput kind="categories" name="category" label="বিভাগের নাম" value={filters.category ?? ""} onChange={(value) => change("category", value)} />
      <CatalogFacetInput kind="series" name="series" label="সিরিজের নাম" value={filters.series ?? ""} onChange={(value) => change("series", value)} />
      <div className="catalog-filter-field"><label htmlFor="kindle-record-type"><SiteText>বইয়ের ধরন</SiteText></label><select id="kindle-record-type" name="record_type" defaultValue={initial.record_type ?? "all"}>{Object.entries({ all: "সব ধরন", digital: "ডিজিটাল বই", manual: "ছাপা বই" }).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div>
      <div className="catalog-filter-field"><label htmlFor="kindle-state"><SiteText>পাঠানোর অবস্থা</SiteText></label><select id="kindle-state" name="state" defaultValue={initial.state ?? ""}><option value=""><SiteText>সব অবস্থা</SiteText></option>{Object.entries(kindleStates).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div>
      <div className="catalog-filter-field"><label htmlFor="kindle-from-date"><SiteText>অনুরোধের শুরুর তারিখ (ঢাকা)</SiteText></label><input id="kindle-from-date" name="from_date" type="date" max="9999-12-31" defaultValue={initial.from_date} /></div>
      <div className="catalog-filter-field"><label htmlFor="kindle-to-date"><SiteText>অনুরোধের শেষ তারিখ (ঢাকা)</SiteText></label><input id="kindle-to-date" name="to_date" type="date" max="9999-12-31" min={initial.from_date} defaultValue={initial.to_date} /></div>
      <div className="catalog-filter-field"><label htmlFor="kindle-sort"><SiteText>কিন্ডলের অনুরোধ সাজান</SiteText></label><select id="kindle-sort" name="sort" defaultValue={initial.sort ?? "-sent_at"}>{Object.entries(kindleHistorySorts).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></div>
    </div><div className="account-actions"><button className="button"><SiteText>ফিল্টার প্রয়োগ করুন</SiteText></button><Link className="button button-quiet" href="/kindle/"><SiteText>সব ফিল্টার সরান</SiteText></Link></div>
  </form>;
}
