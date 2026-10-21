"use client";

import Link from "next/link";
import { Icon } from "./icon";
import { useAdminLanguage } from "./admin-language";

type Field = Readonly<{ name: string; label: string; value: string; options: Readonly<Record<string, string>> }>;
type Props = Readonly<{ pathname: string; search: { label: string; value: string; maxLength: number }; primary: readonly Field[]; advanced?: readonly Field[]; active: boolean }>;

export function AdminDirectoryFilters({ pathname, search, primary, advanced = [], active }: Props) {
  const { t } = useAdminLanguage();
  const field = (item: Field) => <label className="admin-directory-field" key={item.name}><span className="visually-hidden">{t(item.label)}</span><select aria-label={t(item.label)} name={item.name} defaultValue={item.value}>{Object.entries(item.options).map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select></label>;
  return <form className="admin-directory-filters" method="get" role="search"><div className="filter-search"><label className="visually-hidden" htmlFor="admin-directory-query">{t(search.label)}</label><Icon name="search" /><input id="admin-directory-query" name="q" type="search" defaultValue={search.value} maxLength={search.maxLength} placeholder={t(search.label)} /><button className="button"><Icon name="search" /><span>{t("খুঁজুন")}</span></button></div>
    {primary.map(field)}
    {advanced.length > 0 && <details className="admin-more-filters"><summary className="button button-quiet" role="button"><Icon name="settings" />{t("ফিল্টার")}</summary><div className="admin-advanced-fields">{advanced.map(field)}<button className="button">{t("ফিল্টার প্রয়োগ করুন")}</button></div></details>}
    {active && <Link className="text-link admin-clear-filters" href={pathname}><Icon name="refresh" />{t("সব ফিল্টার মুছুন")}</Link>}
  </form>;
}
