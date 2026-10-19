"use client";

import type { CatalogFilters } from "@/lib/catalog-filters";
import { catalogFilterKeys, catalogFilterQuery } from "@/lib/catalog-filters";
import { savedCatalogFilter } from "@/lib/saved-catalog-filter";
import { SavedFilterControls } from "./saved-filter-controls";

export function SavedCatalogFilters({ pathname, values, hidden }: { pathname: string; values: CatalogFilters; hidden: CatalogFilters }) {
  const supported = Object.fromEntries(Object.entries(values).filter(([key]) => key === "q" || catalogFilterKeys.includes(key as typeof catalogFilterKeys[number])));
  return <SavedFilterControls target="catalog" values={supported} href={(parameters) => {
    const conditions = savedCatalogFilter(parameters);
    return conditions ? `${pathname}?${catalogFilterQuery({ ...conditions, ...hidden })}` : null;
  }} />;
}
